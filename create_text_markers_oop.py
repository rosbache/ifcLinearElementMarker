"""
Object-Oriented version of IFC Station Marker Creator
Creates station markers with text annotations at referent locations
"""
import os
import ifcopenshell
import math
from geometry_markers import (
    TriangleMarker, CircleMarker, MarkerElement, 
    TextAnnotation, generate_ifc_guid
)


class StationMarkerFactory:
    """Factory for creating different types of station markers"""
    
    def __init__(self, model, owner_history, context_3d):
        """
        Initialize factory
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        owner_history : IfcOwnerHistory
            IFC owner history
        context_3d : IfcGeometricRepresentationContext
            3D geometric context
        """
        self.model = model
        self.owner_history = owner_history
        self.context_3d = context_3d
        
    def create_triangle_marker(self, station_value, placement, 
                               height=0.5, thickness=0.05, color=(0.0, 0.8, 0.0)):
        """Create a triangle marker for intermediate stations"""
        geometry = TriangleMarker(self.model, height, thickness, color)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Add standard properties
        marker_element.add_properties({
            "StationValue": station_value,
            "MarkerType": "Triangle",
            "Height": height,
            "Thickness": thickness,
            "Color": "Green"
        })
        
        return marker_element
    
    def create_circle_marker(self, station_value, placement,
                            radius=0.5, thickness=0.05, color=(1.0, 0.0, 0.0),
                            marker_type="End"):
        """Create a circle marker for start/end stations"""
        geometry = CircleMarker(self.model, radius, thickness, color)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Add standard properties
        marker_element.add_properties({
            "StationValue": station_value,
            "MarkerType": f"Circle-{marker_type}",
            "Radius": radius,
            "Thickness": thickness,
            "Color": "Red"
        })
        
        return marker_element


class PlacementCalculator:
    """Calculates placements for markers relative to referent positions"""
    
    @staticmethod
    def calculate_perpendicular_direction(placement):
        """
        Calculate perpendicular direction to alignment from referent placement
        
        Parameters:
        -----------
        placement : IfcLocalPlacement
            Referent placement
            
        Returns:
        --------
        tuple : (x, y, z) normalized perpendicular direction
        """
        try:
            rel_placement = placement.RelativePlacement
            if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                align_dir = rel_placement.RefDirection.DirectionRatios
                # Normalize
                length = math.sqrt(align_dir[0]**2 + align_dir[1]**2 + align_dir[2]**2)
                align_normalized = (align_dir[0]/length, align_dir[1]/length, align_dir[2]/length)
                
                # Calculate perpendicular (rotate 90° in XY plane)
                perp_dir = (-align_normalized[1], align_normalized[0], 0.0)
                perp_length = math.sqrt(perp_dir[0]**2 + perp_dir[1]**2)
                
                if perp_length > 0.001:
                    return (perp_dir[0]/perp_length, perp_dir[1]/perp_length, 0.0)
        except Exception:
            pass
        
        return (0.0, 1.0, 0.0)  # Default perpendicular
    
    @staticmethod
    def create_marker_placement(model, referent_placement, height_offset=0.5):
        """
        Create placement for marker above alignment
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        referent_placement : IfcLocalPlacement
            Base referent placement
        height_offset : float
            Vertical offset above centerline
            
        Returns:
        --------
        IfcLocalPlacement
        """
        perp_dir = PlacementCalculator.calculate_perpendicular_direction(referent_placement)
        
        # Position marker above the line
        offset_point = model.create_entity(
            "IfcCartesianPoint", 
            Coordinates=(0.0, 0.0, height_offset)
        )
        
        # Orientation: Y-axis perpendicular to alignment, Z-axis up
        y_direction = model.create_entity("IfcDirection", DirectionRatios=perp_dir)
        z_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
        
        local_axis_placement = model.create_entity(
            "IfcAxis2Placement3D",
            Location=offset_point,
            Axis=z_direction,
            RefDirection=y_direction
        )
        
        return model.create_entity(
            "IfcLocalPlacement",
            PlacementRelTo=referent_placement,
            RelativePlacement=local_axis_placement
        )


class TextLiteralCreator:
    """Creates IFC text literals with styling"""
    
    def __init__(self, model, context_3d):
        """
        Initialize text creator
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        context_3d : IfcGeometricRepresentationContext
            3D geometric context
        """
        self.model = model
        self.context_3d = context_3d
        
    def create_text_literal_representation(self, text, position_offset=(0.0, 0.2, 0.0),
                                          height=1.0, color=(0.0, 0.0, 0.0)):
        """
        Create IfcTextLiteral representation
        
        Parameters:
        -----------
        text : str
            Text content
        position_offset : tuple
            XYZ offset for text position
        height : float
            Text height in meters
        color : tuple
            RGB color values
            
        Returns:
        --------
        IfcShapeRepresentation
        """
        # Create text placement
        text_position = self.model.create_entity("IfcCartesianPoint", Coordinates=position_offset)
        text_axis = self.model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
        text_ref_direction = self.model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
        text_placement = self.model.create_entity(
            "IfcAxis2Placement3D",
            Location=text_position,
            Axis=text_axis,
            RefDirection=text_ref_direction
        )
        
        # Create text literal
        text_literal = self.model.create_entity(
            "IfcTextLiteral",
            Literal=text,
            Placement=text_placement,
            Path="RIGHT"
        )
        
        # Create text style
        text_color_rgb = self.model.create_entity(
            "IfcColourRgb",
            Name="TextColor",
            Red=color[0],
            Green=color[1],
            Blue=color[2]
        )
        
        text_style_char = self.model.create_entity(
            "IfcTextStyleForDefinedFont",
            Colour=text_color_rgb,
            BackgroundColour=None
        )
        
        text_font_style = self.model.create_entity(
            "IfcTextStyleFontModel",
            Name="TextFont",
            FontFamily=["Arial"],
            FontStyle="normal",
            FontVariant="normal",
            FontWeight="normal",
            FontSize=self.model.create_entity("IfcLengthMeasure", wrappedValue=height)
        )
        
        ifc_text_style = self.model.create_entity(
            "IfcTextStyle",
            Name="StationTextStyle",
            TextCharacterAppearance=text_style_char,
            TextFontStyle=text_font_style
        )
        
        # Apply style
        text_styled_item = self.model.create_entity(
            "IfcStyledItem",
            Item=text_literal,
            Styles=[ifc_text_style],
            Name="StationTextStyle"
        )
        
        # Create representation
        return self.model.create_entity(
            "IfcShapeRepresentation",
            ContextOfItems=self.context_3d,
            RepresentationIdentifier="Annotation",
            RepresentationType="Annotation2D",
            Items=[text_literal]
        )
    
    def create_polyline_text_representation(self, text, height=1.0, width_factor=0.6):
        """
        Create polyline-based text representation (fallback)
        
        Parameters:
        -----------
        text : str
            Text content
        height : float
            Text height in meters
        width_factor : float
            Width-to-height ratio
            
        Returns:
        --------
        IfcShapeRepresentation or None
        """
        text_annotation = TextAnnotation(self.model, text, height, width_factor)
        polylines = text_annotation.create_polylines()
        
        if polylines:
            return self.model.create_entity(
                "IfcShapeRepresentation",
                ContextOfItems=self.context_3d,
                RepresentationIdentifier="Annotation",
                RepresentationType="GeometricCurveSet",
                Items=polylines
            )
        return None


class StationMarkerProcessor:
    """Main processor for creating station markers from IFC referents"""
    
    def __init__(self, model, config):
        """
        Initialize processor
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        config : dict
            Configuration dictionary with marker settings
        """
        self.model = model
        self.config = config
        self.project = model.by_type("IfcProject")[0]
        self.owner_history = model.by_type("IfcOwnerHistory")[0]
        
        # Get 3D context
        contexts = model.by_type("IfcGeometricRepresentationContext")
        self.context_3d = None
        for context in contexts:
            if hasattr(context, 'ContextType') and context.ContextType == '3D':
                self.context_3d = context
                break
        if not self.context_3d:
            self.context_3d = contexts[0] if contexts else None
        
        # Initialize helper classes
        self.factory = StationMarkerFactory(model, self.owner_history, self.context_3d)
        self.text_creator = TextLiteralCreator(model, self.context_3d)
        
    def process_referents(self):
        """
        Process all referents and create station markers
        
        Returns:
        --------
        list : Created IFC elements
        """
        referents = self.model.by_type("IfcReferent")
        print(f"Found {len(referents)} IFCREFERENT objects")
        
        # Determine start and end stations
        station_values = []
        for ref in referents:
            if ref.Name:
                try:
                    station_values.append(float(ref.Name))
                except:
                    pass
        
        min_station = min(station_values) if station_values else None
        max_station = max(station_values) if station_values else None
        
        created_elements = []
        
        for referent in referents:
            try:
                elements = self._process_single_referent(
                    referent, min_station, max_station
                )
                created_elements.extend(elements)
            except Exception as e:
                print(f"Error processing referent {referent.Name}: {str(e)}")
                continue
        
        return created_elements
    
    def _process_single_referent(self, referent, min_station, max_station):
        """Process a single referent and create marker elements"""
        if not referent.Name:
            return []
        
        station_value = float(referent.Name)
        display_text = str(int(station_value)) if station_value.is_integer() else f"{station_value:.1f}"
        
        is_start_or_end = (station_value == min_station or station_value == max_station)
        marker_type = "circle" if is_start_or_end else "triangle"
        
        print(f"Processing station: {referent.Name} -> creating {marker_type} with text '{display_text}'")
        
        if not referent.ObjectPlacement:
            return []
        
        # Create placement
        placement = PlacementCalculator.create_marker_placement(
            self.model,
            referent.ObjectPlacement,
            self.config['marker_height_offset']
        )
        
        # Create marker element
        if is_start_or_end:
            marker_element = self.factory.create_circle_marker(
                station_value,
                placement,
                self.config['circle_radius'],
                self.config['circle_thickness'],
                self.config['circle_color']
            )
        else:
            marker_element = self.factory.create_triangle_marker(
                station_value,
                placement,
                self.config['triangle_height'],
                self.config['triangle_thickness'],
                self.config['triangle_color']
            )
        
        # Add additional properties
        marker_element.add_properties({
            "DisplayText": display_text,
            "StationName": referent.Name,
            "TextHeight": self.config['text_height']
        })
        
        # Create text representations
        text_literal_rep = self.text_creator.create_text_literal_representation(
            display_text,
            self.config['text_position_offset'],
            self.config['text_height'],
            self.config['text_color']
        )
        
        # Get marker representation
        marker_rep = marker_element.marker_geometry.create_styled_representation(
            self.context_3d
        )
        
        # Combine representations
        product_shape = self.model.create_entity(
            "IfcProductDefinitionShape",
            Representations=[marker_rep, text_literal_rep]
        )
        
        # Create main marker element
        main_element = self.model.create_entity(
            "IfcBuildingElementProxy",
            GlobalId=generate_ifc_guid(),
            OwnerHistory=self.owner_history,
            Name=f"Station_{display_text}",
            Description=f"{marker_type.capitalize()} marker for station {referent.Name}",
            ObjectType="StationMarker",
            ObjectPlacement=placement,
            Representation=product_shape,
            PredefinedType="USERDEFINED"
        )
        
        # Attach properties
        if marker_element.properties:
            pset = marker_element.create_property_set("Pset_StationText")
            self.model.create_entity(
                "IfcRelDefinesByProperties",
                GlobalId=generate_ifc_guid(),
                OwnerHistory=self.owner_history,
                RelatedObjects=[main_element],
                RelatingPropertyDefinition=pset
            )
        
        elements = [main_element]
        
        # Create fallback polyline text
        polyline_text_rep = self.text_creator.create_polyline_text_representation(
            display_text,
            self.config['text_height'],
            self.config['text_width_factor']
        )
        
        if polyline_text_rep:
            annotation_shape = self.model.create_entity(
                "IfcProductDefinitionShape",
                Representations=[polyline_text_rep]
            )
            
            text_annotation = self.model.create_entity(
                "IfcAnnotation",
                GlobalId=generate_ifc_guid(),
                OwnerHistory=self.owner_history,
                Name=f"Station_Text_{display_text}",
                Description=f"Polyline text annotation for station {referent.Name}",
                ObjectType="TextAnnotation",
                ObjectPlacement=placement,
                Representation=annotation_shape
            )
            
            elements.append(text_annotation)
        
        print(f"Created {marker_type} marker '{display_text}' for station {station_value}")
        
        return elements
    
    def add_to_spatial_structure(self, elements):
        """Add created elements to spatial structure"""
        if not elements:
            return
        
        # Find or create site
        sites = self.model.by_type("IfcSite")
        if sites:
            site = sites[0]
        else:
            site = self.model.create_entity(
                "IfcSite",
                GlobalId=generate_ifc_guid(),
                OwnerHistory=self.owner_history,
                Name="Station Marker Site"
            )
            
            self.model.create_entity(
                "IfcRelAggregates",
                GlobalId=generate_ifc_guid(),
                OwnerHistory=self.owner_history,
                RelatingObject=self.project,
                RelatedObjects=[site]
            )
        
        # Create spatial containment
        self.model.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=generate_ifc_guid(),
            OwnerHistory=self.owner_history,
            RelatedElements=elements,
            RelatingStructure=site
        )


def create_text_markers(input_file, output_file, **config):
    """
    Main function to create text markers at referent locations
    
    Parameters:
    -----------
    input_file : str
        Path to input IFC file
    output_file : str
        Path to output IFC file
    **config : dict
        Configuration parameters (see main section for details)
    """
    # Open IFC file
    model = ifcopenshell.open(input_file)
    
    # Create processor
    processor = StationMarkerProcessor(model, config)
    
    # Process all referents
    created_elements = processor.process_referents()
    
    # Add to spatial structure
    processor.add_to_spatial_structure(created_elements)
    
    # Save model
    model.write(output_file)
    
    # Print summary
    print(f"\nSaved IFC file with markers to: {output_file}")
    print(f"Created {len(created_elements)} elements with text labels")
    print("\nStart and End stations have:")
    print(f"  - RED circular markers ({config['circle_radius']}m radius, {config['circle_thickness']}m thick)")
    print("\nAll other stations have:")
    print(f"  - GREEN triangular markers ({config['triangle_height']}m high, {config['triangle_thickness']}m thick)")
    print("\nAll markers:")
    print(f"  - Positioned {config['marker_height_offset']}m above the alignment line")
    print("  - Oriented perpendicular to alignment direction")
    print(f"  - Include {config['text_height']}m tall text labels")


if __name__ == "__main__":
    # ============================================================================
    # USER CONFIGURABLE PARAMETERS
    # ============================================================================
    
    # Input/Output Files
    INPUT_FILE = "m_f-veg_CL-1000.ifc"
    OUTPUT_FILE = "m_f-veg_CL-1000_with_text_oop.ifc"
    
    # Triangle Marker Settings (for intermediate stations)
    TRIANGLE_HEIGHT = 0.5           # Height of triangle markers in meters
    TRIANGLE_THICKNESS = 0.01       # Thickness of triangle markers in meters
    TRIANGLE_COLOR = (0.0, 0.8, 0.0)  # RGB color (Green)
    
    # Circle Marker Settings (for start/end stations)
    CIRCLE_RADIUS = 0.5             # Radius of circle markers in meters
    CIRCLE_THICKNESS = 0.01         # Thickness of circle markers in meters
    CIRCLE_COLOR = (1.0, 0.0, 0.0)  # RGB color (Red)
    
    # Text Settings
    TEXT_HEIGHT = 1.0               # Height of text labels in meters
    TEXT_WIDTH_FACTOR = 0.6         # Width-to-height ratio for text characters
    TEXT_COLOR = (0.0, 0.0, 0.0)    # RGB color (Black)
    
    # Positioning Settings
    MARKER_HEIGHT_OFFSET = 0.5      # Vertical offset for markers above alignment (meters)
    TEXT_POSITION_OFFSET = (0.0, 0.2, 0.0)  # XYZ offset for text position
    
    # ============================================================================
    # END OF USER CONFIGURABLE PARAMETERS
    # ============================================================================
    
    # Create configuration dictionary
    config = {
        'triangle_height': TRIANGLE_HEIGHT,
        'triangle_thickness': TRIANGLE_THICKNESS,
        'triangle_color': TRIANGLE_COLOR,
        'circle_radius': CIRCLE_RADIUS,
        'circle_thickness': CIRCLE_THICKNESS,
        'circle_color': CIRCLE_COLOR,
        'text_height': TEXT_HEIGHT,
        'text_width_factor': TEXT_WIDTH_FACTOR,
        'text_color': TEXT_COLOR,
        'marker_height_offset': MARKER_HEIGHT_OFFSET,
        'text_position_offset': TEXT_POSITION_OFFSET
    }
    
    # Error handling for the main function call
    try:
        # Check if input file exists        
        if not os.path.exists(INPUT_FILE):
            print(f"Error: Input file '{INPUT_FILE}' does not exist.")
            print("Please check the file path and ensure the file is in the correct location.")
            exit(1)
        
        # Check if input file is readable
        if not os.access(INPUT_FILE, os.R_OK):
            print(f"Error: Input file '{INPUT_FILE}' is not readable.")
            print("Please check file permissions.")
            exit(1)
        
        # Check if output directory exists and is writable
        output_dir = os.path.dirname(OUTPUT_FILE)
        if output_dir and not os.path.exists(output_dir):
            print(f"Error: Output directory '{output_dir}' does not exist.")
            print("Please create the directory or specify a valid output path.")
            exit(1)
        
        if output_dir and not os.access(output_dir, os.W_OK):
            print(f"Error: Output directory '{output_dir}' is not writable.")
            print("Please check directory permissions.")
            exit(1)
        
        print(f"Processing IFC file: {INPUT_FILE}")
        create_text_markers(INPUT_FILE, OUTPUT_FILE, **config)
        
    except ifcopenshell.Error as e:
        print(f"IFC file error: {str(e)}")
        print("The input file may be corrupted or not a valid IFC file.")
        exit(1)
    except PermissionError as e:
        print(f"Permission error: {str(e)}")
        print("Please check file and directory permissions.")
        exit(1)
    except FileNotFoundError as e:
        print(f"File not found error: {str(e)}")
        print("Please check that all required files exist.")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        print("Please check your input file and configuration settings.")
        exit(1)
