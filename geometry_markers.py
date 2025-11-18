"""
Geometry Marker Classes for IFC Alignment Visualization

This module provides a comprehensive object-oriented framework for creating geometric
markers and annotations along IFC alignments. It implements the Strategy pattern with
an abstract base class and concrete implementations for different marker types.

Main Features:
--------------
- Abstract base class (BaseMarker) for consistent marker interface
- Concrete marker implementations: Triangle, Circle, DirectionalArrow
- Automatic IFC geometry creation with proper styling and colors
- Property set management for metadata attachment
- Text annotation with polyline-based character rendering
- Reusable components shared across multiple scripts

Marker Types:
-------------
- TriangleMarker: Green equilateral triangles for intermediate stations
- CircleMarker: Red/orange circular disks for start/end points and slope changes
- DirectionalArrow: Green/red arrows indicating slope direction along alignment
- TextAnnotation: Polyline-based text rendering for maximum viewer compatibility

Architecture:
-------------
The module uses inheritance and composition patterns:
- BaseMarker: Abstract base providing common functionality (styling, placement)
- Concrete classes: Implement specific geometry creation
- MarkerElement: Wrapper combining geometry with IFC element creation
- TextAnnotation: Standalone text rendering using polylines

IFC Entity Creation:
--------------------
All markers are created as IfcExtrudedAreaSolid entities with:
- Profile definition in 2D (XY plane)
- Extrusion direction (typically Y or Z axis)
- Styled representation with RGB colors
- Property sets for metadata storage

Usage:
------
    from geometry_markers import TriangleMarker, MarkerElement
    
    # Create marker geometry
    triangle = TriangleMarker(model, height=0.5, thickness=0.05)
    
    # Wrap in marker element for full IFC integration
    marker = MarkerElement(model, triangle, owner_history, context_3d)
    marker.add_property("StationValue", 100.0)
    
    # Create IFC element
    element = marker.create_ifc_element("Station_100", "Marker", placement)

Author: AFRY
Date: 2025
"""

import ifcopenshell
from abc import ABC, abstractmethod
import uuid
import base64
import logging

__author__ = 'Eirik Rosbach'
__copyright__ = 'Copyright 2025, Eirik Rosbach'
__license__ = ""
__version__ = '0.1'
__email__ = 'eirik.rosbach@afry.com'
__status__ = ' Prototype'

# At module level
logger = logging.getLogger(__name__)

def generate_ifc_guid():
    """
    Generate a valid IFC GUID (Globally Unique Identifier).
    
    Attempts to use ifcopenshell's built-in GUID generator for standard compliance.
    Falls back to manual UUID-to-GUID conversion if the library method is unavailable.
    
    Returns:
        str: A 22-character IFC-compliant GUID string using Base64 encoding with
             IFC-specific character replacements ('+' -> '_', '/' -> '$')
             
    IFC GUID Format:
        - 22 characters long
        - Base64 encoding of 16-byte UUID
        - Uses character set: [0-9A-Za-z_$]
        - Conforms to IFC standard for GlobalId attributes
        
    Example:
        >>> guid = generate_ifc_guid()
        >>> len(guid)
        22
    """
    try:
        # Prefer ifcopenshell's built-in GUID generator for standard compliance
        return ifcopenshell.guid.new()
    except (ImportError, AttributeError):
        # Fallback: Manual GUID generation from UUID4
        # Generate random 128-bit UUID
        random_uuid = uuid.uuid4()
        guid_bytes = random_uuid.bytes
        
        # Convert to Base64 encoding
        guid_base64 = base64.b64encode(guid_bytes).decode('ascii')
        
        # Apply IFC-specific character replacements and truncate
        guid_base64 = guid_base64.replace('+', '_').replace('/', '$').rstrip('=')
        return guid_base64[:22]  # IFC GUIDs are exactly 22 characters


class BaseMarker(ABC):
    """
    Abstract base class for all marker geometry types.
    
    Provides common functionality for creating IFC geometric markers including:
    - Color and style management
    - Styled representation creation
    - Standard placement utilities
    - Extrusion direction helpers
    
    All concrete marker classes must implement:
    - create_geometry(): Generate the specific 3D geometry
    - get_default_color_name(): Return the marker's default color identifier
    
    Attributes:
        model (ifcopenshell.file): The IFC file being modified
        color (tuple): RGB color values as floats in range [0.0, 1.0]
        thickness (float): Extrusion thickness/depth of the marker in meters
        
    Geometry Creation Pattern:
        1. Define 2D profile (IfcArbitraryClosedProfileDef)
        2. Create placement (IfcAxis2Placement3D)
        3. Extrude profile along direction (IfcExtrudedAreaSolid)
        4. Apply styling (IfcSurfaceStyle with color)
        5. Create shape representation (IfcShapeRepresentation)
    
    Example Subclass Implementation:
        >>> class CustomMarker(BaseMarker):
        ...     def create_geometry(self):
        ...         # Create 2D profile
        ...         # Create extrusion
        ...         # Return IfcExtrudedAreaSolid
        ...     def get_default_color_name(self):
        ...         return "CustomColor"
    """
    
    def __init__(self, model, color=(1.0, 1.0, 1.0), thickness=0.05):
        """
        Initialize base marker with common properties.
        
        Args:
            model (ifcopenshell.file): The IFC model being modified
            color (tuple, optional): RGB color as (R, G, B) with values 0.0-1.0.
                                    Defaults to white (1.0, 1.0, 1.0).
            thickness (float, optional): Extrusion depth in meters. Defaults to 0.05m (5cm).
        """
        self.model = model
        self.color = color
        self.thickness = thickness
        
    @abstractmethod
    def create_geometry(self):
        """
        Create the 3D geometry for this marker.
        
        This method must be implemented by all subclasses to define the specific
        geometric shape of the marker. Should return an IfcExtrudedAreaSolid entity.
        
        Returns:
            IfcExtrudedAreaSolid: The 3D solid geometry representing the marker
            
        Implementation Requirements:
            - Define a 2D profile (closed curve in XY plane)
            - Specify extrusion direction (typically Y or Z axis)
            - Set extrusion depth to self.thickness
            - Use helper methods for standard placement and direction
        """
        pass
    
    @abstractmethod
    def get_default_color_name(self):
        """
        Return the default color name for this marker type.
        
        Used for creating styled items and identifying markers visually.
        Should return a descriptive color name like "Green", "Red", etc.
        
        Returns:
            str: Color name identifier (e.g., "Green", "Red", "Orange")
        """
        pass
    
    def create_color_style(self, color_name, transparency=0.0):
        """
        Create IFC color and style entities for marker rendering.
        
        Creates a complete styling hierarchy:
        - IfcColourRgb: RGB color definition
        - IfcSurfaceStyleRendering: Rendering properties
        - IfcSurfaceStyle: Complete style definition
        
        Args:
            color_name (str): Descriptive name for the color (e.g., "Green", "Red")
            transparency (float, optional): Transparency level where 0.0 is fully opaque
                                          and 1.0 is fully transparent. Defaults to 0.0.
                                          
        Returns:
            IfcSurfaceStyle: Complete surface style entity ready for IfcStyledItem
            
        Style Properties:
            - Side: BOTH (applies to both faces of surfaces)
            - ReflectanceMethod: NOTDEFINED (no specific reflectance model)
            - Uses RGB values from self.color attribute
        """
        # Create RGB color entity with component values
        color_rgb = self.model.create_entity(
            "IfcColourRgb", 
            Name=color_name,
            Red=self.color[0],    # Red component (0.0-1.0)
            Green=self.color[1],  # Green component (0.0-1.0)
            Blue=self.color[2]    # Blue component (0.0-1.0)
        )
        
        # Create rendering style with color and transparency
        surface_style_rendering = self.model.create_entity(
            "IfcSurfaceStyleRendering",
            SurfaceColour=color_rgb,
            Transparency=transparency,  # 0.0 = opaque, 1.0 = fully transparent
            ReflectanceMethod="NOTDEFINED"  # No specific shading model
        )
        
        # Create complete surface style
        surface_style = self.model.create_entity(
            "IfcSurfaceStyle",
            Name=f"{color_name}Style",
            Side="BOTH",  # Apply to both front and back faces
            Styles=[surface_style_rendering]
        )
        
        return surface_style
    
    def create_styled_representation(self, context_3d, color_name=None, transparency=0.0):
        """
        Create a styled shape representation combining geometry and visual styling.
        
        This method creates the complete IFC representation including:
        - Geometric shape (from create_geometry())
        - Visual styling (color, transparency)
        - Representation context linkage
        
        Args:
            context_3d (IfcGeometricRepresentationContext): 3D geometric context for the model
            color_name (str, optional): Color identifier. Uses get_default_color_name() if None.
            transparency (float, optional): Transparency from 0.0 (opaque) to 1.0 (transparent).
                                          Defaults to 0.0.
                                          
        Returns:
            IfcShapeRepresentation: Complete shape representation ready to attach to product
            
        Representation Properties:
            - Identifier: "Body" (indicates this is the main solid body)
            - Type: "SweptSolid" (geometry created by sweeping/extruding)
            - Items: Contains the IfcExtrudedAreaSolid geometry
            
        Note:
            The IfcStyledItem is created for styling but is not explicitly returned.
            It associates the style with the geometry through the IFC model.
        """
        # Use default color if not specified
        if color_name is None:
            color_name = self.get_default_color_name()
        
        # Create the 3D geometry
        geometry = self.create_geometry()
        
        # Create the visual style
        style = self.create_color_style(color_name, transparency)
        
        # Associate style with geometry (required for rendering)
        self.model.create_entity(
            "IfcStyledItem",
            Item=geometry,
            Styles=[style],
            Name=f"{color_name}StyledItem"
        )
        
        # Create the shape representation
        representation = self.model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=context_3d,
            RepresentationIdentifier="Body",  # Main body representation
            RepresentationType="SweptSolid",  # Extruded geometry type
            Items=[geometry]
        )
        
        return representation
    
    def _create_standard_placement(self, offset=(0.0, 0.0, 0.0)):
        """
        Create standard axis placement for profile extrusion.
        
        Creates an IfcAxis2Placement3D defining the local coordinate system for
        the extrusion operation. Default orientation:
        - Origin: At specified offset
        - Z-axis (Axis): Points in +Y direction (extrusion direction)
        - X-axis (RefDirection): Points in +X direction
        
        Args:
            offset (tuple, optional): XYZ coordinates for placement origin.
                                     Defaults to (0.0, 0.0, 0.0).
                                     
        Returns:
            IfcAxis2Placement3D: Placement entity for extrusion positioning
            
        Coordinate System:
            - Local X: (1, 0, 0) - horizontal right
            - Local Y: (0, 1, 0) - extrusion direction
            - Local Z: (0, 0, 1) - derived from X and Y (upward)
        """
        origin = self.model.create_entity("IfcCartesianPoint", Coordinates=offset)
        axis_z = self.model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
        axis_x = self.model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
        
        return self.model.create_entity(
            "IfcAxis2Placement3D",
            Location=origin,
            Axis=axis_z,        # Z-axis of placement (extrusion direction)
            RefDirection=axis_x  # X-axis of placement
        )
    
    def _create_extrusion_direction(self, direction=(0.0, 1.0, 0.0)):
        """
        Create extrusion direction vector.
        
        Defines the direction along which the 2D profile will be extruded
        to create the 3D solid.
        
        Args:
            direction (tuple, optional): XYZ direction ratios for extrusion.
                                        Defaults to (0, 1, 0) - Y-axis.
                                        
        Returns:
            IfcDirection: Direction entity for IfcExtrudedAreaSolid
        """
        return self.model.create_entity("IfcDirection", DirectionRatios=direction)


class TriangleMarker(BaseMarker):
    """
    Triangular marker for intermediate station points.
    
    Creates an equilateral triangle pointing upward, used to mark regular stations
    along the alignment. The triangle is green by default and oriented perpendicular
    to the alignment direction.
    
    Geometry:
        - Base: Horizontal edge at Y=0
        - Apex: Point at Y=height
        - Width: Calculated as height * 0.866 for equilateral proportions
        - Profile: Triangle in XY plane, extruded along Y-axis
        - Color: Green (0.0, 0.8, 0.0) by default
    
    Attributes:
        model (ifcopenshell.file): The IFC model
        height (float): Height of triangle from base to apex in meters
        thickness (float): Extrusion depth in meters
        color (tuple): RGB color values (0.0-1.0 range)
        
    Usage:
        >>> triangle = TriangleMarker(model, height=0.5, thickness=0.05)
        >>> geometry = triangle.create_geometry()
    """
    
    def __init__(self, model, height=0.5, thickness=0.05, color=(0.0, 0.8, 0.0)):
        """
        Initialize triangle marker for intermediate stations.
        
        Args:
            model (ifcopenshell.file): The IFC model being modified
            height (float, optional): Triangle height in meters. Defaults to 0.5m.
            thickness (float, optional): Extrusion depth in meters. Defaults to 0.05m (5cm).
            color (tuple, optional): RGB color (0-1 range). Defaults to green (0.0, 0.8, 0.0).
        """
        super().__init__(model, color, thickness)
        self.height = height
        
    def get_default_color_name(self):
        """Return default color name for triangle markers."""
        return "Green"
    
    def create_geometry(self):
        """
        Create equilateral triangle geometry.
        
        Constructs a triangle profile in the XY plane and extrudes it along the Y-axis
        to create a thin triangular disk marker.
        
        Returns:
            IfcExtrudedAreaSolid: Triangle geometry with equilateral proportions
            
        Triangle Vertices:
            - P1: (-base_width/2, 0) - bottom left
            - P2: (+base_width/2, 0) - bottom right
            - P3: (0, height) - apex (top center)
            
        Dimensions:
            - Base width: height * 0.866 (sqrt(3)/2 for equilateral triangle)
            - Height: As specified in constructor
            - Thickness: Extrusion depth along Y-axis
            
        Coordinate System:
            - Profile: XY plane with base on X-axis
            - Extrusion: Along +Y direction
            - Result: Triangle perpendicular to Y-axis
        """
        # Calculate base width for equilateral triangle (height * sqrt(3)/2)
        base_width = self.height * 0.866
        
        # Create triangle vertices: base at Y=0, apex at Y=height
        p1 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(-base_width/2, 0.0))  # Left base corner
        p2 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(base_width/2, 0.0))   # Right base corner
        p3 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(0.0, self.height))    # Apex
        
        # Create closed polyline forming triangle outline
        polyline = self.model.create_entity("IfcPolyline", Points=[p1, p2, p3, p1])
        
        # Create profile from closed polyline
        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",              # Solid area profile
            ProfileName="TriangleProfile",
            OuterCurve=polyline
        )
        
        # Set up extrusion placement and direction
        placement = self._create_standard_placement()
        extrusion_direction = self._create_extrusion_direction()
        
        # Create extruded solid by sweeping triangle profile
        return self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=placement,
            ExtrudedDirection=extrusion_direction,
            Depth=self.thickness  # Extrusion depth
        )


class CircleMarker(BaseMarker):
    """
    Circular marker for start/end stations and slope change points.
    
    Creates a circular disk marker, typically used to indicate special locations
    along the alignment such as the start point, end point, or slope change locations.
    
    Geometry:
        - Shape: Circular disk (filled circle)
        - Radius: Configurable radius from center
        - Profile: Circle in XY plane, extruded along Y-axis
        - Color: Red (1.0, 0.0, 0.0) by default for start/end, orange for slope changes
    
    Attributes:
        model (ifcopenshell.file): The IFC model
        radius (float): Radius of the circle in meters
        thickness (float): Extrusion depth in meters
        color (tuple): RGB color values (0.0-1.0 range)
        
    Usage:
        >>> # Red circle for start/end stations
        >>> circle = CircleMarker(model, radius=0.5, color=(1.0, 0.0, 0.0))
        >>> # Orange circle for slope changes
        >>> slope_circle = CircleMarker(model, radius=0.4, color=(1.0, 0.5, 0.0))
    """
    
    def __init__(self, model, radius=0.5, thickness=0.05, color=(1.0, 0.0, 0.0)):
        """
        Initialize circle marker for special station points.
        
        Args:
            model (ifcopenshell.file): The IFC model being modified
            radius (float, optional): Circle radius in meters. Defaults to 0.5m.
            thickness (float, optional): Extrusion depth in meters. Defaults to 0.05m (5cm).
            color (tuple, optional): RGB color (0-1 range). Defaults to red (1.0, 0.0, 0.0).
        """
        super().__init__(model, color, thickness)
        self.radius = radius
        
    def get_default_color_name(self):
        """Return default color name for circle markers."""
        return "Red"
    
    def create_geometry(self):
        """
        Create circular disk geometry.
        
        Constructs a circular profile in the XY plane and extrudes it along the Y-axis
        to create a thin circular disk marker.
        
        Returns:
            IfcExtrudedAreaSolid: Circular disk geometry
            
        Circle Properties:
            - Center: (0, 0) in profile plane
            - Radius: As specified in constructor
            - Thickness: Extrusion depth along Y-axis
            
        Coordinate System:
            - Profile: XY plane with center at origin
            - Extrusion: Along +Y direction
            - Result: Circular disk perpendicular to Y-axis
        """
        # Create circle center point in 2D profile plane
        center = self.model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
        
        # Create circle geometry with specified radius
        circle = self.model.create_entity(
            "IfcCircle",
            Position=self.model.create_entity("IfcAxis2Placement2D", Location=center),
            Radius=self.radius  # Circle radius in profile plane
        )
        
        # Create profile from circle curve
        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",              # Solid area profile
            ProfileName="CircleProfile",
            OuterCurve=circle
        )
        
        # Set up extrusion placement and direction
        placement = self._create_standard_placement()
        extrusion_direction = self._create_extrusion_direction()
        
        # Create extruded solid by sweeping circular profile
        return self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=placement,
            ExtrudedDirection=extrusion_direction,
            Depth=self.thickness  # Extrusion depth
        )


class DirectionalArrow(BaseMarker):
    """
    Directional arrow marker for indicating slope direction.
    
    Creates a triangular arrow that points along the alignment direction, showing
    whether the slope is upward (positive grade) or downward (negative grade).
    Color automatically changes based on slope direction.
    
    Geometry:
        - Shape: Triangular arrow pointing in +X direction
        - Base: Two points on Y-axis (width apart)
        - Apex: Point at (length, 0) forming arrow tip
        - Profile: Triangle in XY plane, extruded along Z-axis
        - Orientation: Points forward along alignment when placed correctly
    
    Color Coding:
        - Green (0.0, 0.8, 0.0): Upward slope (positive grade)
        - Red (1.0, 0.0, 0.0): Downward slope (negative grade)
    
    Attributes:
        model (ifcopenshell.file): The IFC model
        length (float): Arrow length from base to tip in meters
        width (float): Arrow width at base in meters
        thickness (float): Extrusion depth in meters
        is_upward (bool): True for upward slope, False for downward
        color (tuple): RGB color (auto-set based on is_upward)
        
    Usage:
        >>> # Green arrow for upward slope
        >>> arrow_up = DirectionalArrow(model, length=0.6, is_upward=True)
        >>> # Red arrow for downward slope
        >>> arrow_down = DirectionalArrow(model, length=0.6, is_upward=False)
        
    Note:
        Arrow points in +X direction in its local coordinate system.
        Use create_arrow_placement() to orient it along the alignment.
    """
    
    def __init__(self, model, length=0.6, width=0.3, thickness=0.05, 
                 is_upward=True):
        """
        Initialize directional arrow for slope indication.
        
        Args:
            model (ifcopenshell.file): The IFC model being modified
            length (float, optional): Arrow length in meters. Defaults to 0.6m.
            width (float, optional): Arrow width at base in meters. Defaults to 0.3m.
            thickness (float, optional): Extrusion depth in meters. Defaults to 0.05m (5cm).
            is_upward (bool, optional): True for upward slope (green), False for downward (red).
                                       Defaults to True.
        """
        # Set color based on slope direction
        color = (0.0, 0.8, 0.0) if is_upward else (1.0, 0.0, 0.0)
        super().__init__(model, color, thickness)
        self.length = length
        self.width = width
        self.is_upward = is_upward
        
    def get_default_color_name(self):
        """Return default color name based on slope direction."""
        return "Green" if self.is_upward else "Red"
    
    def create_geometry(self):
        """
        Create triangular arrow geometry pointing along X-axis.
        
        Constructs an arrow-shaped triangle in the XY plane and extrudes it along
        the Z-axis. The arrow points in the +X direction, which will align with
        the alignment direction when properly placed.
        
        Returns:
            IfcExtrudedAreaSolid: Arrow geometry pointing forward
            
        Arrow Vertices:
            - P1: (0, -width/2) - Base left
            - P2: (0, +width/2) - Base right  
            - P3: (length, 0) - Arrow tip
            
        Dimensions:
            - Length: From base (X=0) to tip (X=length)
            - Width: Full width at base
            - Thickness: Extrusion depth along Z-axis
            
        Coordinate System:
            - Profile: XY plane with base on Y-axis, tip on +X
            - Extrusion: Along +Z direction (vertical)
            - Result: Horizontal arrow when Z is up
            
        Note:
            The arrow points in +X direction. Use create_arrow_placement()
            with alignment direction to orient it correctly along the centerline.
        """
        # Create triangle vertices: base centered on Y-axis, tip pointing +X
        p1 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(0.0, -self.width/2))  # Base left
        p2 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(0.0, self.width/2))   # Base right
        p3 = self.model.create_entity("IfcCartesianPoint", 
                                     Coordinates=(self.length, 0.0))    # Arrow tip
        
        # Create closed polyline forming arrow outline
        polyline = self.model.create_entity("IfcPolyline", Points=[p1, p2, p3, p1])
        
        # Create profile from arrow polyline
        profile = self.model.create_entity(
            "IfcArbitraryClosedProfileDef",
            ProfileType="AREA",              # Solid area profile
            ProfileName="ArrowProfile",
            OuterCurve=polyline
        )
        
        # Create placement at origin for horizontal arrow
        origin = self.model.create_entity("IfcCartesianPoint", 
                                         Coordinates=(0.0, 0.0, 0.0))
        placement = self.model.create_entity("IfcAxis2Placement3D", Location=origin)
        
        # Extrude vertically along Z-axis
        extrusion_direction = self.model.create_entity(
            "IfcDirection", 
            DirectionRatios=(0.0, 0.0, 1.0)  # Vertical extrusion
        )
        
        # Create extruded solid by sweeping arrow profile
        return self.model.create_entity(
            "IfcExtrudedAreaSolid",
            SweptArea=profile,
            Position=placement,
            ExtrudedDirection=extrusion_direction,
            Depth=self.thickness  # Extrusion depth
        )


class MarkerElement:
    """
    Complete marker element wrapper for IFC integration.
    
    This class wraps a marker geometry object (Triangle, Circle, or Arrow) and provides
    functionality to:
    - Attach metadata via property sets
    - Create complete IFC building elements
    - Manage element naming and description
    - Handle property set creation and assignment
    
    Acts as a bridge between the pure geometry classes (BaseMarker subclasses) and
    full IFC product entities (IfcBuildingElementProxy with properties).
    
    Attributes:
        model (ifcopenshell.file): The IFC file being modified
        marker_geometry (BaseMarker): The geometric marker (Triangle, Circle, Arrow)
        owner_history (IfcOwnerHistory): IFC ownership and history information
        context_3d (IfcGeometricRepresentationContext): 3D context for geometry
        properties (dict): Dictionary of property name-value pairs
        
    Workflow:
        1. Create MarkerElement with geometry
        2. Add properties using add_property() or add_properties()
        3. Create IFC element using create_ifc_element()
        4. Property set automatically attached to element
        
    Example:
        >>> # Create geometry
        >>> triangle = TriangleMarker(model, height=0.5)
        >>> # Wrap in marker element
        >>> marker = MarkerElement(model, triangle, owner_history, context_3d)
        >>> # Add metadata
        >>> marker.add_properties({
        ...     "StationValue": 100.0,
        ...     "MarkerType": "Triangle"
        ... })
        >>> # Create IFC element
        >>> element = marker.create_ifc_element(
        ...     "Station_100",
        ...     "Marker at station 100",
        ...     placement
        ... )
    """
    
    def __init__(self, model, marker_geometry, owner_history, context_3d):
        """
        Initialize marker element wrapper.
        
        Args:
            model (ifcopenshell.file): The IFC model being modified
            marker_geometry (BaseMarker): Geometry object (Triangle, Circle, or Arrow)
            owner_history (IfcOwnerHistory): IFC ownership and history information
            context_3d (IfcGeometricRepresentationContext): 3D geometric context
        """
        self.model = model
        self.marker_geometry = marker_geometry
        self.owner_history = owner_history
        self.context_3d = context_3d
        self.properties = {}  # Dictionary to store custom properties
        
    def add_property(self, name, value):
        """
        Add a single property to this marker element.
        
        Properties are stored and later converted to an IFC property set when
        creating the IFC element.
        
        Args:
            name (str): Property name identifier
            value (any): Property value (float, int, str, or bool)
        """
        self.properties[name] = value
        
    def add_properties(self, property_dict):
        """
        Add multiple properties at once from a dictionary.
        
        Convenient method for bulk property assignment. All properties will be
        included in the property set when the IFC element is created.
        
        Args:
            property_dict (dict): Dictionary mapping property names to values
        """
        self.properties.update(property_dict)
        
    def create_property_set(self, pset_name="Pset_MarkerInformation"):
        """
        Create an IFC property set from stored properties.
        
        Converts the properties dictionary into an IfcPropertySet with properly
        typed IfcPropertySingleValue entities. Automatically handles type conversion
        for float, int, bool, and string values.
        
        Args:
            pset_name (str, optional): Name for the property set.
                                      Defaults to "Pset_MarkerInformation".
                                      
        Returns:
            IfcPropertySet: Property set entity containing all stored properties
            
        Property Type Mapping:
            - float -> IfcReal
            - int -> IfcInteger
            - bool -> IfcBoolean
            - str -> IfcLabel
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
