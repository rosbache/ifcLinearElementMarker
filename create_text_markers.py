import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
import uuid
import base64
import math

def generate_ifc_guid():
    """Generate a valid IFC GUID"""
    random_uuid = uuid.uuid4()
    guid_bytes = random_uuid.bytes
    guid_base64 = base64.b64encode(guid_bytes).decode('ascii')
    guid_base64 = guid_base64.replace('+', '_').replace('/', '$').rstrip('=')
    return guid_base64[:22]

def create_triangle_geometry(model, height=0.5, thickness=0.01):
    """
    Create a 1 cm thick triangular solid, vertical, with base at origin, tip pointing upward
    Triangle is 0.5m high, flat base on the line, tip extends upward
    """
    # Create triangle profile - flat base on the line, tip pointing up
    # Profile defined in local XY, will map to world XZ (perpendicular-vertical plane)
    base_width = height * 0.866  # Proportional base for equilateral-ish triangle
    
    # Triangle vertices - in 2D profile space
    # Profile X will map to world X (perpendicular to alignment)
    # Profile Y will map to world Z (vertical/up direction)
    # Base on the line (Y=0), tip at top (Y=height)
    p1 = model.create_entity("IfcCartesianPoint", Coordinates=(-base_width/2, 0.0))  # Left base on line
    p2 = model.create_entity("IfcCartesianPoint", Coordinates=(base_width/2, 0.0))   # Right base on line
    p3 = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, height))         # Tip pointing up
    
    # Create closed polyline for triangle
    polyline = model.create_entity("IfcPolyline", Points=[p1, p2, p3, p1])
    
    # Create arbitrary profile definition
    profile = model.create_entity("IfcArbitraryClosedProfileDef",
                                 ProfileType="AREA",
                                 ProfileName="Triangle",
                                 OuterCurve=polyline)
    
    # Create placement for extrusion
    # Map profile to XZ plane: profile X→world X, profile Y→world Z, extrude along world Y
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    # Axis (extrusion direction) along Y
    axis_z = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
    # RefDirection (profile X direction) along X
    axis_x = model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
    # This creates: Profile X→World X, Profile Y→World Z, Extrusion→World Y
    placement = model.create_entity("IfcAxis2Placement3D",
                                   Location=origin,
                                   Axis=axis_z,
                                   RefDirection=axis_x)
    
    # Create extrusion direction (along Y for thickness - perpendicular to XZ profile plane)
    extrusion_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
    
    # Create extruded area solid (1 cm thick along Y)
    extruded_solid = model.create_entity("IfcExtrudedAreaSolid",
                                        SweptArea=profile,
                                        Position=placement,
                                        ExtrudedDirection=extrusion_direction,
                                        Depth=thickness)
    
    return extruded_solid

def create_circle_geometry(model, radius=0.5, thickness=0.01):
    """
    Create a 1 cm thick circular disk
    Circle has 0.5m radius, oriented vertically (in XZ plane)
    """
    # Create circle profile centered at origin
    center = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    circle = model.create_entity("IfcCircle", 
                                 Position=model.create_entity("IfcAxis2Placement2D", Location=center),
                                 Radius=radius)
    
    # Create arbitrary profile definition
    profile = model.create_entity("IfcArbitraryClosedProfileDef",
                                 ProfileType="AREA",
                                 ProfileName="Circle",
                                 OuterCurve=circle)
    
    # Create placement for extrusion
    # Map profile to XZ plane: profile XY→world XZ, extrude along world Y
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    # Axis (extrusion direction) along Y
    axis_z = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
    # RefDirection (profile X direction) along X
    axis_x = model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
    placement = model.create_entity("IfcAxis2Placement3D",
                                   Location=origin,
                                   Axis=axis_z,
                                   RefDirection=axis_x)
    
    # Create extrusion direction (along Y for thickness)
    extrusion_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
    
    # Create extruded area solid (1 cm thick along Y)
    extruded_solid = model.create_entity("IfcExtrudedAreaSolid",
                                        SweptArea=profile,
                                        Position=placement,
                                        ExtrudedDirection=extrusion_direction,
                                        Depth=thickness)
    
    return extruded_solid

def create_text_geometry(model, text_content, height=5.0, width_factor=0.6):
    """
    Create 3D text geometry using polylines for each character
    Returns a list of IfcPolyline objects representing the text
    """
    # Simple character definitions as polylines (normalized to 1 unit height)
    # Each character is defined as a list of polylines, where each polyline is a list of (x, y) points
    char_definitions = {
        '0': [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]],  # Rectangle
        '1': [[(0.5, 0), (0.5, 1)], [(0.2, 0.8), (0.5, 1)], [(0.3, 0), (0.7, 0)]],  # Vertical line with base
        '2': [[(0, 0.7), (0, 1), (1, 1), (1, 0.5), (0, 0.5), (0, 0), (1, 0)]],  # Number 2
        '3': [[(0, 1), (1, 1), (1, 0.6), (0.5, 0.6)], [(1, 0.6), (1, 0), (0, 0)]],  # Number 3
        '4': [[(0, 1), (0, 0.5), (1, 0.5)], [(0.7, 0), (0.7, 1)]],  # Number 4
        '5': [[(1, 1), (0, 1), (0, 0.5), (1, 0.5), (1, 0), (0, 0)]],  # Number 5
        '6': [[(1, 1), (0, 1), (0, 0), (1, 0), (1, 0.5), (0, 0.5)]],  # Number 6
        '7': [[(0, 1), (1, 1), (1, 0)]],  # Number 7
        '8': [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)], [(0, 0.5), (1, 0.5)]],  # Number 8
        '9': [[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0.5), (1, 0.5)]],  # Number 9
        '.': [[(0.4, 0), (0.6, 0), (0.6, 0.2), (0.4, 0.2), (0.4, 0)]],  # Period
        ' ': []  # Space
    }
    
    polylines = []
    x_offset = 0
    char_width = width_factor * height
    char_spacing = char_width * 1.2
    
    for char in text_content:
        if char in char_definitions:
            char_lines = char_definitions[char]
            for line_points in char_lines:
                # Scale and position the character
                scaled_points = []
                for x, y in line_points:
                    scaled_x = x_offset + x * char_width
                    scaled_y = y * height
                    point = model.create_entity("IfcCartesianPoint", Coordinates=(scaled_x, scaled_y, 0.0))
                    scaled_points.append(point)
                
                if scaled_points:  # Only create polyline if there are points
                    polyline = model.create_entity("IfcPolyline", Points=scaled_points)
                    polylines.append(polyline)
        
        x_offset += char_spacing
    
    return polylines

def create_text_markers(input_file, output_file):
    """
    Create readable text objects at all IFCREFERENT locations displaying station values
    """
    # Open the IFC file
    model = ifcopenshell.open(input_file)
    
    # Get all IFCREFERENT objects
    referents = model.by_type("IfcReferent")
    print(f"Found {len(referents)} IFCREFERENT objects")
    
    # Get the project and owner history
    project = model.by_type("IfcProject")[0]
    owner_history = model.by_type("IfcOwnerHistory")[0]
    
    # Get the geometric representation context
    contexts = model.by_type("IfcGeometricRepresentationContext")
    context_3d = None
    for context in contexts:
        if hasattr(context, 'ContextType') and context.ContextType == '3D':
            context_3d = context
            break
    
    if not context_3d:
        context_3d = contexts[0] if contexts else None
    
    # Create text marker objects
    text_elements = []
    
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
    
    for referent in referents:
        try:
            # Extract station value from the name
            station_name = referent.Name
            if station_name:
                # Parse the numeric value (e.g., "10.000000" -> 10)
                station_value = float(station_name)
                # Create display text - use integer if possible, otherwise rounded to 1 decimal
                if station_value.is_integer():
                    display_text = str(int(station_value))
                else:
                    display_text = f"{station_value:.1f}"
                
                # Determine if this is start or end station
                is_start_or_end = (station_value == min_station or station_value == max_station)
                marker_type = "circle" if is_start_or_end else "triangle"
                
                print(f"Processing station: {station_name} -> creating {marker_type} with text '{display_text}'")
                
                # Get the placement of the referent
                placement = referent.ObjectPlacement
                if not placement:
                    continue
                
                # Create geometry based on station type
                if is_start_or_end:
                    # Create circle geometry (0.5m radius, 1 cm thick, vertical)
                    marker_solid = create_circle_geometry(model, radius=0.5, thickness=0.01)
                    color_name = "Red"
                    color_values = (1.0, 0.0, 0.0)
                    marker_height = 0.5  # Circle radius for offset
                else:
                    # Create triangle geometry (0.5m high, 1 cm thick, vertical)
                    marker_solid = create_triangle_geometry(model, height=0.5, thickness=0.01)
                    color_name = "Green"
                    color_values = (0.0, 0.8, 0.0)
                    marker_height = 0.5  # Triangle height for offset
                
                # Create color for the marker
                color_rgb = model.create_entity("IfcColourRgb", 
                                               Name=color_name,
                                               Red=color_values[0],
                                               Green=color_values[1],
                                               Blue=color_values[2])
                
                surface_style_rendering = model.create_entity("IfcSurfaceStyleRendering",
                                                             SurfaceColour=color_rgb,
                                                             Transparency=0.0,
                                                             ReflectanceMethod="NOTDEFINED")
                
                style_name = f"{color_name}Marker"
                surface_style = model.create_entity("IfcSurfaceStyle",
                                                   Name=style_name,
                                                   Side="BOTH",
                                                   Styles=[surface_style_rendering])
                
                styled_item = model.create_entity("IfcStyledItem",
                                                 Item=marker_solid,
                                                 Styles=[surface_style],
                                                 Name=f"{marker_type}Style")
                
                # Create shape representation for the marker
                marker_representation = model.create_entity("IfcShapeRepresentation",
                                                             ContextOfItems=context_3d,
                                                             RepresentationIdentifier="Body",
                                                             RepresentationType="SweptSolid",
                                                             Items=[marker_solid])
                
                # Create text using both methods for maximum compatibility
                text_height = 0.5
                
                # METHOD 1: IfcTextLiteral (modern approach, may not be visible in all viewers)
                # Create text placement - position text next to marker
                text_position = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.2, 0.0))
                text_axis = model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
                text_ref_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
                text_placement = model.create_entity("IfcAxis2Placement3D",
                                                     Location=text_position,
                                                     Axis=text_axis,
                                                     RefDirection=text_ref_direction)
                
                # Create IfcTextLiteral
                text_literal = model.create_entity("IfcTextLiteral",
                                                   Literal=display_text,
                                                   Placement=text_placement,
                                                   Path="RIGHT")
                
                # Create text style with font and size
                text_color = model.create_entity("IfcColourRgb",
                                                Name="Black",
                                                Red=0.0,
                                                Green=0.0,
                                                Blue=0.0)
                
                text_style = model.create_entity("IfcTextStyleForDefinedFont",
                                                Colour=text_color,
                                                BackgroundColour=None)
                
                text_font_style = model.create_entity("IfcTextStyleFontModel",
                                                     Name="TextFont",
                                                     FontFamily=["Arial"],
                                                     FontStyle="normal",
                                                     FontVariant="normal",
                                                     FontWeight="normal",
                                                     FontSize=model.create_entity("IfcLengthMeasure", wrappedValue=text_height))
                
                # Create IfcTextStyle
                ifc_text_style = model.create_entity("IfcTextStyle",
                                                     Name="StationTextStyle",
                                                     TextCharacterAppearance=text_style,
                                                     TextFontStyle=text_font_style)
                
                # Apply style to text literal via IfcStyledItem
                text_styled_item = model.create_entity("IfcStyledItem",
                                                       Item=text_literal,
                                                       Styles=[ifc_text_style],
                                                       Name="StationTextStyle")
                
                # Create text representation using IfcTextLiteral
                text_literal_representation = model.create_entity("IfcShapeRepresentation",
                                                                 ContextOfItems=context_3d,
                                                                 RepresentationIdentifier="Annotation",
                                                                 RepresentationType="Annotation2D",
                                                                 Items=[text_literal])
                
                # Create product definition shape with marker and text literal
                product_shape = model.create_entity("IfcProductDefinitionShape",
                                                  Representations=[marker_representation, text_literal_representation])
                
                # Position marker above the line
                # Marker is perpendicular to the alignment direction
                
                # Try to extract the alignment direction from the placement
                try:
                    rel_placement = placement.RelativePlacement
                    if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                        # Get the alignment direction
                        align_dir = rel_placement.RefDirection.DirectionRatios
                        # Normalize
                        import math
                        length = math.sqrt(align_dir[0]**2 + align_dir[1]**2 + align_dir[2]**2)
                        align_normalized = (align_dir[0]/length, align_dir[1]/length, align_dir[2]/length)
                        
                        # Calculate perpendicular direction (rotate 90 degrees in XY plane)
                        # Perpendicular in horizontal plane: if align is (x,y,0), perp is (-y,x,0)
                        perp_dir = (-align_normalized[1], align_normalized[0], 0.0)
                        perp_length = math.sqrt(perp_dir[0]**2 + perp_dir[1]**2)
                        if perp_length > 0.001:
                            perp_normalized = (perp_dir[0]/perp_length, perp_dir[1]/perp_length, 0.0)
                        else:
                            perp_normalized = (0.0, 1.0, 0.0)  # Default perpendicular
                    else:
                        # Default perpendicular to X-axis is Y-axis
                        perp_normalized = (0.0, 1.0, 0.0)
                except Exception:
                    # Default perpendicular direction
                    perp_normalized = (0.0, 1.0, 0.0)
                
                # Position marker above the line by marker_height
                # For triangles: base at line, tip above
                # For circles: center at line level, extends up and down
                offset_point = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, marker_height))
                
                # Create axis directions for proper orientation
                # Y-axis points perpendicular to alignment (triangle thickness direction)
                y_direction = model.create_entity("IfcDirection", DirectionRatios=perp_normalized)
                # Z-axis points up (triangle height direction)
                z_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
                # X-axis is perpendicular to both (triangle base width direction)
                
                local_axis_placement = model.create_entity("IfcAxis2Placement3D", 
                                                         Location=offset_point,
                                                         Axis=z_direction,
                                                         RefDirection=y_direction)
                
                # Create local placement that references the referent's placement
                local_placement = model.create_entity("IfcLocalPlacement",
                                                    PlacementRelTo=placement,
                                                    RelativePlacement=local_axis_placement)
                
                # Create IfcBuildingElementProxy for the triangle marker (better for solid geometry)
                text_marker = model.create_entity("IfcBuildingElementProxy",
                                                GlobalId=generate_ifc_guid(),
                                                OwnerHistory=owner_history,
                                                Name=f"Station_{display_text}",
                                                Description=f"Green triangle marker for station {station_name}",
                                                ObjectType="StationMarker",
                                                ObjectPlacement=local_placement,
                                                Representation=product_shape,
                                                PredefinedType="USERDEFINED")
                
                text_elements.append(text_marker)
                
                # METHOD 2: Create separate IfcAnnotation for polyline text (fallback for viewers that don't support IfcTextLiteral)
                text_polylines = create_text_geometry(model, display_text, text_height)
                
                if text_polylines:
                    # Create shape representation with the text polylines
                    text_polyline_representation = model.create_entity("IfcShapeRepresentation",
                                                                      ContextOfItems=context_3d,
                                                                      RepresentationIdentifier="Annotation",
                                                                      RepresentationType="GeometricCurveSet",
                                                                      Items=text_polylines)
                    
                    # Create product definition shape for annotation
                    annotation_shape = model.create_entity("IfcProductDefinitionShape",
                                                          Representations=[text_polyline_representation])
                    
                    # Create IfcAnnotation for the polyline text
                    text_annotation = model.create_entity("IfcAnnotation",
                                                    GlobalId=generate_ifc_guid(),
                                                    OwnerHistory=owner_history,
                                                    Name=f"Station_Text_{display_text}",
                                                    Description=f"Polyline text annotation for station {station_name}",
                                                    ObjectType="TextAnnotation",
                                                    ObjectPlacement=local_placement,
                                                    Representation=annotation_shape)
                    
                    text_elements.append(text_annotation)
                
                # Create property set with text and station information
                properties = [
                    model.create_entity("IfcPropertySingleValue",
                                       Name="StationValue",
                                       NominalValue=model.create_entity("IfcReal", wrappedValue=station_value)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="DisplayText", 
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue=display_text)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="TextHeight", 
                                       NominalValue=model.create_entity("IfcLengthMeasure", wrappedValue=text_height)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="TriangleHeight", 
                                       NominalValue=model.create_entity("IfcLengthMeasure", wrappedValue=0.5)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="TriangleThickness", 
                                       NominalValue=model.create_entity("IfcLengthMeasure", wrappedValue=0.01)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="MarkerType", 
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue="TriangleMarker")),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="Color", 
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue="Green")),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="StationName", 
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue=station_name)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="ViewDirection", 
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue="TopDown"))
                ]
                
                property_set = model.create_entity("IfcPropertySet",
                                                 GlobalId=generate_ifc_guid(),
                                                 OwnerHistory=owner_history,
                                                 Name="Pset_StationText",
                                                 HasProperties=properties)
                
                # Relate property set to the text marker
                property_rel = model.create_entity("IfcRelDefinesByProperties",
                                                 GlobalId=generate_ifc_guid(),
                                                 OwnerHistory=owner_history,
                                                 RelatedObjects=[text_marker],
                                                 RelatingPropertyDefinition=property_set)
                
                print(f"Created text marker '{display_text}' for station {station_value}")
                
        except Exception as e:
            print(f"Error processing referent {referent.Name}: {str(e)}")
            continue
    
    # Add all text markers to the spatial structure
    if text_elements:
        # Find or create a site to contain the markers
        sites = model.by_type("IfcSite")
        if sites:
            site = sites[0]
        else:
            # Create a default site if none exists
            site = model.create_entity("IfcSite",
                                     GlobalId=generate_ifc_guid(),
                                     OwnerHistory=owner_history,
                                     Name="Station Text Site")
            
            # Relate site to project
            site_rel = model.create_entity("IfcRelAggregates",
                                         GlobalId=generate_ifc_guid(),
                                         OwnerHistory=owner_history,
                                         RelatingObject=project,
                                         RelatedObjects=[site])
        
        # Create spatial containment relationship
        containment_rel = model.create_entity("IfcRelContainedInSpatialStructure",
                                            GlobalId=generate_ifc_guid(),
                                            OwnerHistory=owner_history,
                                            RelatedElements=text_elements,
                                            RelatingStructure=site)
    
    # Save the modified model
    model.write(output_file)
    print(f"\nSaved IFC file with markers to: {output_file}")
    print(f"Created {len(text_elements)} elements with text labels")
    print("\nStart and End stations have:")
    print("  - RED circular markers (0.5m radius, 1 cm thick)")
    print("\nAll other stations have:")
    print("  - GREEN triangular markers (0.5m high, 1 cm thick)")
    print("\nAll markers:")
    print("  - Positioned 0.5m above the alignment line")
    print("  - Oriented perpendicular to alignment direction")
    print("  - Include 0.5m tall text labels (using TWO separate entities for compatibility):")
    print("    1. IfcTextLiteral with IfcTextStyle (modern, styled text - part of marker)")
    print("    2. IfcAnnotation with polyline geometry (fallback for viewers that don't support text literals)")

if __name__ == "__main__":
    input_file = "m_f-veg_CL-1000.ifc"
    output_file = "m_f-veg_CL-1000_with_text.ifc"
    
    create_text_markers(input_file, output_file)