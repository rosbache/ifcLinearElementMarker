"""
Geometry marker classes for IFC alignment markers
Provides object-oriented interface for creating different marker types
"""

import ifcopenshell
from abc import ABC, abstractmethod
import uuid
import base64


def generate_ifc_guid():
    """Generate a valid IFC GUID"""
    random_uuid = uuid.uuid4()
    guid_bytes = random_uuid.bytes
    guid_base64 = base64.b64encode(guid_bytes).decode('ascii')
    guid_base64 = guid_base64.replace('+', '_').replace('/', '$').rstrip('=')
    return guid_base64[:22]


class BaseMarker(ABC):
    """Abstract base class for all marker geometry types"""
    
    def __init__(self, model, color=(1.0, 1.0, 1.0), thickness=0.05):
        """
        Initialize base marker
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        color : tuple
            RGB color values (0.0-1.0)
        thickness : float
            Thickness of the marker in meters
        """
        self.model = model
        self.color = color
        self.thickness = thickness
        
    @abstractmethod
    def create_geometry(self):
        """Create the 3D geometry for this marker. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def get_default_color_name(self):
        """Return the default color name for this marker type"""
        pass
    
    def create_color_style(self, color_name, transparency=0.0):
        """
        Create IFC color and style entities
        
        Parameters:
        -----------
        color_name : str
            Name for the color
        transparency : float
            Transparency value (0.0 = opaque, 1.0 = fully transparent)
            
        Returns:
        --------
        IfcSurfaceStyle
        """
        color_rgb = self.model.create_entity(
            "IfcColourRgb", 
            Name=color_name,
            Red=self.color[0],
            Green=self.color[1],
            Blue=self.color[2]
        )
        
        surface_style_rendering = self.model.create_entity(
            "IfcSurfaceStyleRendering",
            SurfaceColour=color_rgb,
            Transparency=transparency,
            ReflectanceMethod="NOTDEFINED"
        )
        
        surface_style = self.model.create_entity(
            "IfcSurfaceStyle",
            Name=f"{color_name}Style",
            Side="BOTH",
            Styles=[surface_style_rendering]
        )
        
        return surface_style
    
    def create_styled_representation(self, context_3d, color_name=None, transparency=0.0):
        """
        Create styled shape representation with geometry
        
        Parameters:
        -----------
        context_3d : IfcGeometricRepresentationContext
            3D geometric context
        color_name : str, optional
            Color name (uses default if not provided)
        transparency : float
            Transparency value (0.0-1.0)
            
        Returns:
        --------
        IfcShapeRepresentation
        """
        if color_name is None:
            color_name = self.get_default_color_name()
            
        geometry = self.create_geometry()
        style = self.create_color_style(color_name, transparency)
        
        styled_item = self.model.create_entity(
            "IfcStyledItem",
            Item=geometry,
            Styles=[style],
            Name=f"{color_name}StyledItem"
        )
        
        representation = self.model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=context_3d,
            RepresentationIdentifier="Body",
            RepresentationType="SweptSolid",
            Items=[geometry]
        )
        
        return representation
    
    def _create_standard_placement(self, offset=(0.0, 0.0, 0.0)):
        """
        Create standard placement for extrusion
        
        Parameters:
        -----------
        offset : tuple
            XYZ offset for the origin point
            
        Returns:
        --------
        IfcAxis2Placement3D
        """
        origin = self.model.create_entity("IfcCartesianPoint", Coordinates=offset)
        axis_z = self.model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
        axis_x = self.model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
        
        return self.model.create_entity(
            "IfcAxis2Placement3D",
            Location=origin,
            Axis=axis_z,
            RefDirection=axis_x
        )
    
    def _create_extrusion_direction(self, direction=(0.0, 1.0, 0.0)):
        """Create extrusion direction entity"""
        return self.model.create_entity("IfcDirection", DirectionRatios=direction)


class TriangleMarker(BaseMarker):
    """Triangular marker for intermediate stations"""
    
    def __init__(self, model, height=0.5, thickness=0.05, color=(0.0, 0.8, 0.0)):
        """
        Initialize triangle marker
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        height : float
            Height of the triangle in meters
        thickness : float
            Thickness of the triangle in meters
        color : tuple
            RGB color (default: green)
        """
        super().__init__(model, color, thickness)
        self.height = height
        
    def get_default_color_name(self):
        return "Green"
    
    def create_geometry(self):
        """
        Create triangle geometry
        Triangle base on the line, tip pointing upward
        Profile in XY plane, extruded along Y
        """
        base_width = self.height * 0.866  # Equilateral proportions
        
        # Triangle vertices - base at Y=0, tip at Y=height
        p1 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(-base_width/2, 0.0))
        p2 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(base_width/2, 0.0))
        p3 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(0.0, self.height))
        
        polyline = self.model.create_entity("IfcPolyline", Points=[p1, p2, p3, p1])
        
        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            ProfileName="TriangleProfile",
            OuterCurve=polyline
        )
        
        placement = self._create_standard_placement()
        extrusion_direction = self._create_extrusion_direction()
        
        return self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=placement,
            ExtrudedDirection=extrusion_direction,
            Depth=self.thickness
        )


class CircleMarker(BaseMarker):
    """Circular marker for start/end stations or slope changes"""
    
    def __init__(self, model, radius=0.5, thickness=0.05, color=(1.0, 0.0, 0.0)):
        """
        Initialize circle marker
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        radius : float
            Radius of the circle in meters
        thickness : float
            Thickness of the circle in meters
        color : tuple
            RGB color (default: red)
        """
        super().__init__(model, color, thickness)
        self.radius = radius
        
    def get_default_color_name(self):
        return "Red"
    
    def create_geometry(self):
        """
        Create circular disk geometry
        Circle in XY plane, extruded along Y
        """
        center = self.model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
        
        circle = self.model.create_entity(
            "IfcCircle",
            Position=self.model.create_entity("IfcAxis2Placement2D", Location=center),
            Radius=self.radius
        )
        
        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            ProfileName="CircleProfile",
            OuterCurve=circle
        )
        
        placement = self._create_standard_placement()
        extrusion_direction = self._create_extrusion_direction()
        
        return self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=placement,
            ExtrudedDirection=extrusion_direction,
            Depth=self.thickness
        )


class DirectionalArrow(BaseMarker):
    """Directional arrow marker for slope indication"""
    
    def __init__(self, model, length=0.6, width=0.3, thickness=0.05, 
                 is_upward=True):
        """
        Initialize directional arrow
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        length : float
            Length of the arrow in meters
        width : float
            Width of the arrow in meters
        thickness : float
            Thickness of the arrow in meters
        is_upward : bool
            True for upward slope (green), False for downward (red)
        """
        color = (0.0, 0.8, 0.0) if is_upward else (1.0, 0.0, 0.0)
        super().__init__(model, color, thickness)
        self.length = length
        self.width = width
        self.is_upward = is_upward
        
    def get_default_color_name(self):
        return "Green" if self.is_upward else "Red"
    
    def create_geometry(self):
        """
        Create arrow/triangle geometry pointing along X-axis
        Triangle in XY plane, extruded along Z
        """
        # Triangle pointing in +X direction
        p1 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(0.0, -self.width/2))
        p2 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(0.0, self.width/2))
        p3 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(self.length, 0.0))
        
        polyline = self.model.create_entity("IfcPolyline", Points=[p1, p2, p3, p1])
        
        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",
            ProfileName="ArrowProfile",
            OuterCurve=polyline
        )
        
        # For horizontal arrow, extrude along Z
        origin = self.model.create_entity("IfcCartesianPoint", 
                                         Coordinates=(0.0, 0.0, 0.0))
        placement = self.model.create_entity("IfcAxis2Placement3D", Location=origin)
        
        extrusion_direction = self.model.create_entity(
            "IfcDirection", 
            DirectionRatios=(0.0, 0.0, 1.0)
        )
        
        return self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=placement,
            ExtrudedDirection=extrusion_direction,
            Depth=self.thickness
        )


class MarkerElement:
    """
    Complete marker element with geometry, placement, and properties
    Wraps marker geometry with IFC element creation
    """
    
    def __init__(self, model, marker_geometry, owner_history, context_3d):
        """
        Initialize marker element
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        marker_geometry : BaseMarker
            The marker geometry object
        owner_history : IfcOwnerHistory
            IFC owner history
        context_3d : IfcGeometricRepresentationContext
            3D geometric context
        """
        self.model = model
        self.marker_geometry = marker_geometry
        self.owner_history = owner_history
        self.context_3d = context_3d
        self.properties = {}
        
    def add_property(self, name, value):
        """
        Add a property to this marker
        
        Parameters:
        -----------
        name : str
            Property name
        value : any
            Property value (float, int, str, or bool)
        """
        self.properties[name] = value
        
    def add_properties(self, property_dict):
        """
        Add multiple properties at once
        
        Parameters:
        -----------
        property_dict : dict
            Dictionary of property name: value pairs
        """
        self.properties.update(property_dict)
        
    def create_property_set(self, pset_name="Pset_MarkerInformation"):
        """
        Create IFC property set from stored properties
        
        Parameters:
        -----------
        pset_name : str
            Name for the property set
            
        Returns:
        --------
        IfcPropertySet
        """
        ifc_properties = []
        
        for name, value in self.properties.items():
            if isinstance(value, float):
                ifc_value = self.model.create_entity("IfcReal", wrappedValue=value)
            elif isinstance(value, int):
                ifc_value = self.model.create_entity("IfcInteger", wrappedValue=value)
            elif isinstance(value, bool):
                ifc_value = self.model.create_entity("IfcBoolean", wrappedValue=value)
            else:
                ifc_value = self.model.create_entity("IfcLabel", wrappedValue=str(value))
                
            ifc_properties.append(
                self.model.create_entity(
                    "IfcPropertySingleValue",
                    Name=name,
                    NominalValue=ifc_value
                )
            )
        
        return self.model.create_entity(
            "IfcPropertySet",
            GlobalId=generate_ifc_guid(),
            OwnerHistory=self.owner_history,
            Name=pset_name,
            HasProperties=ifc_properties
        )
    
    def create_ifc_element(self, name, description, placement, 
                          color_name=None, transparency=0.0,
                          pset_name="Pset_MarkerInformation"):
        """
        Create the IFC building element proxy with geometry and properties
        
        Parameters:
        -----------
        name : str
            Element name
        description : str
            Element description
        placement : IfcLocalPlacement
            IFC placement for the element
        color_name : str, optional
            Color name (uses default if not provided)
        transparency : float
            Transparency value (0.0-1.0)
        pset_name : str
            Property set name
            
        Returns:
        --------
        IfcBuildingElementProxy
        """
        # Create styled representation
        representation = self.marker_geometry.create_styled_representation(
            self.context_3d,
            color_name,
            transparency
        )
        
        product_shape = self.model.create_entity(
            "IfcProductDefinitionShape",
            Representations=[representation]
        )
        
        element = self.model.create_entity(
            "IfcBuildingElementProxy",
            GlobalId=generate_ifc_guid(),
            OwnerHistory=self.owner_history,
            Name=name,
            Description=description,
            ObjectType="Marker",
            ObjectPlacement=placement,
            Representation=product_shape,
            PredefinedType="USERDEFINED"
        )
        
        # Attach property set if properties exist
        if self.properties:
            pset = self.create_property_set(pset_name)
            self.model.create_entity(
                "IfcRelDefinesByProperties",
                GlobalId=generate_ifc_guid(),
                OwnerHistory=self.owner_history,
                RelatedObjects=[element],
                RelatingPropertyDefinition=pset
            )
        
        return element


class TextAnnotation:
    """Text annotation with polyline-based character rendering"""
    
    # Character definitions as polylines (normalized to 1 unit height)
    CHAR_DEFINITIONS = {
        '0': [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]],
        '1': [[(0.5, 0), (0.5, 1)], [(0.2, 0.8), (0.5, 1)], [(0.3, 0), (0.7, 0)]],
        '2': [[(0, 0.7), (0, 1), (1, 1), (1, 0.5), (0, 0.5), (0, 0), (1, 0)]],
        '3': [[(0, 1), (1, 1), (1, 0.6), (0.5, 0.6)], [(1, 0.6), (1, 0), (0, 0)]],
        '4': [[(0, 1), (0, 0.5), (1, 0.5)], [(0.7, 0), (0.7, 1)]],
        '5': [[(1, 1), (0, 1), (0, 0.5), (1, 0.5), (1, 0), (0, 0)]],
        '6': [[(1, 1), (0, 1), (0, 0), (1, 0), (1, 0.5), (0, 0.5)]],
        '7': [[(0, 1), (1, 1), (1, 0)]],
        '8': [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], [(0, 0.5), (1, 0.5)]],
        '9': [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0.5), (1, 0.5)]],
        '.': [[(0.4, 0), (0.6, 0), (0.6, 0.2), (0.4, 0.2), (0.4, 0)]],
        ' ': []
    }
    
    def __init__(self, model, text, height=1.0, width_factor=0.6):
        """
        Initialize text annotation
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        text : str
            Text content to render
        height : float
            Height of text in meters
        width_factor : float
            Width-to-height ratio for characters
        """
        self.model = model
        self.text = text
        self.height = height
        self.width_factor = width_factor
        
    def create_polylines(self):
        """
        Create polyline geometry for the text
        
        Returns:
        --------
        list of IfcPolyline
        """
        polylines = []
        x_offset = 0
        char_width = self.width_factor * self.height
        char_spacing = char_width * 1.2
        
        for char in self.text:
            if char in self.CHAR_DEFINITIONS:
                char_lines = self.CHAR_DEFINITIONS[char]
                for line_points in char_lines:
                    scaled_points = []
                    for x, y in line_points:
                        scaled_x = x_offset + x * char_width
                        scaled_y = y * self.height
                        point = self.model.create_entity(
                            "IfcCartesianPoint", 
                            Coordinates=(scaled_x, scaled_y, 0.0)
                        )
                        scaled_points.append(point)
                    
                    if scaled_points:
                        polyline = self.model.create_entity("IfcPolyline", Points=scaled_points)
                        polylines.append(polyline)
            
            x_offset += char_spacing
        
        return polylines
