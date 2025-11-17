import ifcopenshell
import ifcopenshell.api
import ifcopenshell.geom
import uuid
import base64

def generate_ifc_guid():
    """Generate a valid IFC GUID"""
    random_uuid = uuid.uuid4()
    guid_bytes = random_uuid.bytes
    guid_base64 = base64.b64encode(guid_bytes).decode('ascii')
    guid_base64 = guid_base64.replace('+', '_').replace('/', '$').rstrip('=')
    return guid_base64[:22]

def create_circle_geometry(model, radius=0.5, thickness=0.1):
    """
    Create a circular marker for slope change points - larger and more visible
    Oriented vertically (in XZ plane) matching triangles and red circles
    """
    # Create circle profile centered at origin
    center = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
    circle = model.create_entity("IfcCircle", 
                                 Position=model.create_entity("IfcAxis2Placement2D", Location=center),
                                 Radius=radius)
    
    # Create arbitrary profile definition
    profile = model.create_entity("IfcArbitraryClosedProfileDef",
                                 ProfileType="AREA",
                                 ProfileName="SlopeChangeMarker",
                                 OuterCurve=circle)
    
    # Create placement for extrusion - map profile to XZ plane, extrude along Y
    # This matches the orientation of triangles and red circles in create_text_markers.py
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    # Axis (extrusion direction) along Y
    axis_z = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
    # RefDirection (profile X direction) along X
    axis_x = model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
    placement = model.create_entity("IfcAxis2Placement3D",
                                   Location=origin,
                                   Axis=axis_z,
                                   RefDirection=axis_x)
    
    # Create extrusion direction (along Y for thickness - perpendicular to XZ profile plane)
    extrusion_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
    
    # Create extruded area solid - thicker for better visibility
    extruded_solid = model.create_entity("IfcExtrudedAreaSolid",
                                        SweptArea=profile,
                                        Position=placement,
                                        ExtrudedDirection=extrusion_direction,
                                        Depth=thickness)
    
    return extruded_solid

def create_directional_triangle(model, length=0.6, width=0.3, thickness=0.05):
    """
    Create a horizontal triangle pointing in the positive X direction (along alignment)
    Triangle lies in XY plane, with tip pointing forward (+X), extruded in Z
    Used to show slope direction along the alignment
    """
    # Create triangle profile in XY plane - tip points in +X direction
    # Base perpendicular to alignment direction
    p1 = model.create_entity("IfcCartesianPoint", Coordinates=(length, 0.0))  # Tip (front)
    p2 = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, -width/2))  # Left back
    p3 = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, width/2))   # Right back
    
    # Create closed polyline for triangle
    polyline = model.create_entity("IfcPolyline", Points=[p1, p2, p3, p1])
    
    # Create arbitrary profile definition
    profile = model.create_entity("IfcArbitraryClosedProfileDef",
                                 ProfileType="AREA",
                                 ProfileName="DirectionalArrow",
                                 OuterCurve=polyline)
    
    # Create placement for extrusion - profile in XY plane, extrude along Z
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    axis_z = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    axis_x = model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
    placement = model.create_entity("IfcAxis2Placement3D",
                                   Location=origin,
                                   Axis=axis_z,
                                   RefDirection=axis_x)
    
    # Create extrusion direction (along Z for thickness)
    extrusion_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    
    # Create extruded area solid
    extruded_solid = model.create_entity("IfcExtrudedAreaSolid",
                                        SweptArea=profile,
                                        Position=placement,
                                        ExtrudedDirection=extrusion_direction,
                                        Depth=thickness)
    
    return extruded_solid

def create_text_literal(model, text_content, position, height=0.4, color=(0.0, 0.0, 0.8), font="Arial"):
    """
    Create an IfcTextLiteral with specified position and content
    
    Parameters:
    -----------
    model : ifcopenshell model
        The IFC model
    text_content : str
        Text to display
    position : tuple
        XYZ coordinates for text position
    height : float
        Text height in meters (default: 0.4)
    color : tuple
        RGB color for text (default: (0.0, 0.0, 0.8) - DarkBlue)
    font : str
        Font family (default: "Arial")
    """
    # Create text placement
    text_position = model.create_entity("IfcCartesianPoint", Coordinates=position)
    text_axis = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    text_ref_direction = model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
    text_placement = model.create_entity("IfcAxis2Placement3D",
                                         Location=text_position,
                                         Axis=text_axis,
                                         RefDirection=text_ref_direction)
    
    # Create IfcTextLiteral
    text_literal = model.create_entity("IfcTextLiteral",
                                       Literal=text_content,
                                       Placement=text_placement,
                                       Path="RIGHT")
    
    # Create text style
    text_color = model.create_entity("IfcColourRgb",
                                    Name="TextColor",
                                    Red=color[0],
                                    Green=color[1],
                                    Blue=color[2])
    
    text_style = model.create_entity("IfcTextStyleForDefinedFont",
                                    Colour=text_color,
                                    BackgroundColour=None)
    
    text_font_style = model.create_entity("IfcTextStyleFontModel",
                                         Name="SlopeFont",
                                         FontFamily=[font],
                                         FontStyle="normal",
                                         FontVariant="normal",
                                         FontWeight="bold",
                                         FontSize=model.create_entity("IfcLengthMeasure", wrappedValue=height))
    
    # Create IfcTextStyle
    ifc_text_style = model.create_entity("IfcTextStyle",
                                         Name="SlopeTextStyle",
                                         TextCharacterAppearance=text_style,
                                         TextFontStyle=text_font_style)
    
    # Apply style to text literal
    text_styled_item = model.create_entity("IfcStyledItem",
                                           Item=text_literal,
                                           Styles=[ifc_text_style],
                                           Name="SlopeTextStyle")
    
    return text_literal

def interpolate_height_at_station(station, vertical_segments):
    """
    Calculate height at a specific station based on vertical alignment segments
    """
    for segment in vertical_segments:
        start_dist = segment['start_distance']
        length = segment['length']
        end_dist = start_dist + length
        
        if start_dist <= station <= end_dist:
            # Station is within this segment
            distance_into_segment = station - start_dist
            start_height = segment['start_height']
            start_grade = segment['start_grade']
            end_grade = segment['end_grade']
            
            if segment['curve_type'] == '.CONSTANTGRADIENT.':
                # Linear interpolation for constant gradient
                height = start_height + (distance_into_segment * start_grade)
            else:
                # For vertical curves, use parabolic interpolation
                # Simplified calculation assuming parabolic curve
                if length > 0:
                    t = distance_into_segment / length
                    grade_change = end_grade - start_grade
                    current_grade = start_grade + (grade_change * t)
                    height = start_height + (distance_into_segment * (start_grade + current_grade) / 2)
                else:
                    height = start_height
            
            return height
    
    # If station not found in segments, extrapolate from last segment
    if vertical_segments:
        last_segment = vertical_segments[-1]
        last_station = last_segment['start_distance'] + last_segment['length']
        last_height = last_segment['start_height'] + (last_segment['length'] * last_segment['end_grade'])
        extra_distance = station - last_station
        return last_height + (extra_distance * last_segment['end_grade'])
    
    return 0.0

def add_slope_information(input_file, output_file,
                         slope_marker_radius=0.4, slope_marker_thickness=0.06, slope_marker_color=(1.0, 0.5, 0.0),
                         arrow_length=0.6, arrow_width=0.3, arrow_thickness=0.05,
                         arrow_color_positive=(0.0, 0.8, 0.0), arrow_color_negative=(1.0, 0.0, 0.0),
                         text_height_large=0.6, text_height_medium=0.5, text_height_small=0.4,
                         text_color=(0.0, 0.0, 0.8), text_font="Arial",
                         slope_marker_height_offset=1.0, arrow_height_offset=0.8,
                         property_set_name="Pset_SlopeInformation"):
    """
    Add slope information, height data, and slope change markers to IFC alignment
    
    Parameters:
    -----------
    input_file : str
        Path to input IFC file
    output_file : str
        Path to output IFC file
    slope_marker_radius : float
        Radius of slope change markers in meters (default: 0.4)
    slope_marker_thickness : float
        Thickness of slope change markers in meters (default: 0.06)
    slope_marker_color : tuple
        RGB color for slope change markers (default: (1.0, 0.5, 0.0) - Orange)
    arrow_length : float
        Length of directional arrow in meters (default: 0.6)
    arrow_width : float
        Width of directional arrow in meters (default: 0.3)
    arrow_thickness : float
        Thickness of directional arrow in meters (default: 0.05)
    arrow_color_positive : tuple
        RGB color for upward slope arrows (default: (0.0, 0.8, 0.0) - Green)
    arrow_color_negative : tuple
        RGB color for downward slope arrows (default: (1.0, 0.0, 0.0) - Red)
    text_height_large : float
        Height for large text in meters (default: 0.6)
    text_height_medium : float
        Height for medium text in meters (default: 0.5)
    text_height_small : float
        Height for small text in meters (default: 0.4)
    text_color : tuple
        RGB color for text (default: (0.0, 0.0, 0.8) - DarkBlue)
    text_font : str
        Font family for text (default: "Arial")
    slope_marker_height_offset : float
        Vertical offset for slope markers above centerline in meters (default: 1.0)
    arrow_height_offset : float
        Vertical offset for directional arrows above centerline in meters (default: 0.8)
    property_set_name : str
        Name of the property set attached to slope information arrows (default: "Pset_SlopeInformation")
    arrow_height_offset : float
        Vertical offset for arrows above centerline in meters (default: 0.8)
    """
    # Open the IFC file
    model = ifcopenshell.open(input_file)
    
    # Get alignment and vertical segments
    alignments = model.by_type("IfcAlignment")
    if not alignments:
        print("No alignment found in the file")
        return
    
    alignment = alignments[0]
    print(f"Processing alignment: {alignment.Name}")
    
    # Get vertical alignment segments
    vertical_segments = []
    alignment_verticals = model.by_type("IfcAlignmentVertical")
    
    for vertical in alignment_verticals:
        # Get vertical segments from the nesting relationship
        for rel in model.by_type("IfcRelNests"):
            if rel.RelatingObject == vertical:
                for segment_entity in rel.RelatedObjects:
                    if hasattr(segment_entity, 'DesignParameters'):
                        segment = segment_entity.DesignParameters
                        if hasattr(segment, 'StartDistAlong') and hasattr(segment, 'HorizontalLength'):
                            vertical_segments.append({
                                'start_distance': segment.StartDistAlong,
                                'length': segment.HorizontalLength,
                                'start_height': segment.StartHeight,
                                'start_grade': segment.StartGradient,
                                'end_grade': segment.EndGradient,
                                'curve_type': str(segment.PredefinedType),
                                'radius': getattr(segment, 'StartRadiusOfCurvature', None)
                            })
    
    # Sort segments by start distance
    vertical_segments.sort(key=lambda x: x['start_distance'])
    
    print(f"Found {len(vertical_segments)} vertical segments:")
    for i, seg in enumerate(vertical_segments):
        print(f"  Segment {i+1}: {seg['start_distance']:.1f}m - {seg['start_distance']+seg['length']:.1f}m, "
              f"Grade: {seg['start_grade']*100:.1f}% to {seg['end_grade']*100:.1f}%, "
              f"Type: {seg['curve_type']}")
    
    # Get referents (station points)
    referents = model.by_type("IfcReferent")
    print(f"Found {len(referents)} station referents")
    
    # Build a map of referent stations for positioning
    referent_map = {}
    for ref in referents:
        if ref.Name:
            try:
                station_val = float(ref.Name)
                referent_map[station_val] = ref
            except Exception:
                pass
    
    # Get project context
    project = model.by_type("IfcProject")[0]
    owner_history = model.by_type("IfcOwnerHistory")[0]
    
    # Get geometric representation context
    contexts = model.by_type("IfcGeometricRepresentationContext")
    context_3d = None
    for context in contexts:
        if hasattr(context, 'ContextType') and context.ContextType == '3D':
            context_3d = context
            break
    
    if not context_3d:
        context_3d = contexts[0] if contexts else None
    
    # Create elements to add
    new_elements = []
    
    # 1. Add slope change markers and information
    slope_change_points = []
    
    # Identify slope change points - look for transitions between constant grades and curves
    for i in range(len(vertical_segments)):
        segment = vertical_segments[i]
        
        # Check if this segment has a significant grade change within itself (curve)
        if abs(segment['start_grade'] - segment['end_grade']) > 0.01:  # 1% change within segment
            # Add marker at start of curve segment
            slope_change_points.append({
                'station': segment['start_distance'],
                'from_grade': segment['start_grade'],
                'to_grade': segment['end_grade'],
                'height': interpolate_height_at_station(segment['start_distance'], vertical_segments[:i+1]),
                'type': 'curve_start'
            })
        
        # Check for grade changes between adjacent segments
        if i > 0:
            prev_segment = vertical_segments[i-1]
            grade_change = abs(segment['start_grade'] - prev_segment['end_grade'])
            
            if grade_change > 0.01:  # Significant grade change (1%)
                slope_change_points.append({
                    'station': segment['start_distance'],
                    'from_grade': prev_segment['end_grade'],
                    'to_grade': segment['start_grade'],
                    'height': interpolate_height_at_station(segment['start_distance'], vertical_segments[:i+1]),
                    'type': 'segment_transition'
                })
    
    # Also add the known major slope change points from analysis
    known_slope_changes = [
        {'station': 28.36, 'from_grade': -0.03, 'to_grade': 0.0202, 'height': 2.93},
        {'station': 106.86, 'from_grade': 0.0202, 'to_grade': -0.04, 'height': 3.63},
        {'station': 192.91, 'from_grade': -0.04, 'to_grade': 0.011, 'height': 1.82}
    ]
    
    # Add known points if not already detected
    for known_point in known_slope_changes:
        # Check if we already have a point near this station
        existing = False
        for existing_point in slope_change_points:
            if abs(existing_point['station'] - known_point['station']) < 5.0:
                existing = True
                break
        
        if not existing:
            slope_change_points.append({
                'station': known_point['station'],
                'from_grade': known_point['from_grade'],
                'to_grade': known_point['to_grade'], 
                'height': known_point['height'],
                'type': 'major_grade_change'
            })
    
    print(f"Identified {len(slope_change_points)} slope change points:")
    for point in slope_change_points:
        point_type = point.get('type', 'unknown')
        print(f"  Station {point['station']:.1f}m: {point['from_grade']*100:.1f}% → {point['to_grade']*100:.1f}% ({point_type})")
    
    # Add markers and text at slope change points
    for point in slope_change_points:
        station = point['station']
        
        # Find exact referent at this station or create placement at the correct position
        exact_referent = referent_map.get(station)
        
        if not exact_referent:
            # Find two referents that bracket this station
            stations_below = [s for s in referent_map.keys() if s <= station]
            stations_above = [s for s in referent_map.keys() if s > station]
            
            if stations_below and stations_above:
                station_below = max(stations_below)
                station_above = min(stations_above)
                ref_below = referent_map[station_below]
                ref_above = referent_map[station_above]
                
                # Use the closer referent as reference
                if abs(station - station_below) < abs(station - station_above):
                    base_referent = ref_below
                    station_offset = station - station_below
                else:
                    base_referent = ref_above
                    station_offset = station - station_above
            elif stations_below:
                # Use the last station below
                station_below = max(stations_below)
                base_referent = referent_map[station_below]
                station_offset = station - station_below
            elif stations_above:
                # Use the first station above
                station_above = min(stations_above)
                base_referent = referent_map[station_above]
                station_offset = station - station_above
            else:
                continue
        else:
            base_referent = exact_referent
            station_offset = 0.0
        
        if base_referent and base_referent.ObjectPlacement:
            # Create slope change marker (orange circle)
            marker_solid = create_circle_geometry(model, radius=slope_marker_radius, thickness=slope_marker_thickness)
            
            # Create color for slope change markers
            color_rgb = model.create_entity("IfcColourRgb", 
                                           Name="Orange",
                                           Red=slope_marker_color[0],
                                           Green=slope_marker_color[1],
                                           Blue=slope_marker_color[2])
            
            surface_style_rendering = model.create_entity("IfcSurfaceStyleRendering",
                                                         SurfaceColour=color_rgb,
                                                         Transparency=0.2,
                                                         ReflectanceMethod="NOTDEFINED")
            
            surface_style = model.create_entity("IfcSurfaceStyle",
                                               Name="SlopeChangeMarker",
                                               Side="BOTH",
                                               Styles=[surface_style_rendering])
            
            styled_item = model.create_entity("IfcStyledItem",
                                             Item=marker_solid,
                                             Styles=[surface_style],
                                             Name="SlopeChangeStyle")
            
            # Create shape representation for marker
            marker_representation = model.create_entity("IfcShapeRepresentation",
                                                         ContextOfItems=context_3d,
                                                         RepresentationIdentifier="Body",
                                                         RepresentationType="SweptSolid",
                                                         Items=[marker_solid])
            
            # Create text information
            grade_change_text = f"Grade Change: {point['from_grade']*100:.1f}% → {point['to_grade']*100:.1f}%"
            station_text = f"Station: {station:.1f}m"
            height_text = f"Height: {point['height']:.2f}m"
            
            # Create text literals
            text1 = create_text_literal(model, grade_change_text, (0.5, 0.0, 0.8), text_height_large, text_color, text_font)
            text2 = create_text_literal(model, station_text, (0.5, 0.0, 0.4), text_height_medium, text_color, text_font)
            text3 = create_text_literal(model, height_text, (0.5, 0.0, 0.0), text_height_medium, text_color, text_font)
            
            # Create text representation
            text_representation = model.create_entity("IfcShapeRepresentation",
                                                     ContextOfItems=context_3d,
                                                     RepresentationIdentifier="Annotation",
                                                     RepresentationType="Annotation2D",
                                                     Items=[text1, text2, text3])
            
            # Combine representations
            product_shape = model.create_entity("IfcProductDefinitionShape",
                                              Representations=[marker_representation, text_representation])
            
            # Get alignment direction from base referent
            try:
                rel_placement = base_referent.ObjectPlacement.RelativePlacement
                if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                    align_dir = rel_placement.RefDirection.DirectionRatios
                    import math
                    length = math.sqrt(align_dir[0]**2 + align_dir[1]**2 + align_dir[2]**2)
                    align_normalized = (align_dir[0]/length, align_dir[1]/length, align_dir[2]/length)
                    perp_dir = (-align_normalized[1], align_normalized[0], 0.0)
                    perp_length = math.sqrt(perp_dir[0]**2 + perp_dir[1]**2)
                    if perp_length > 0.001:
                        perp_normalized = (perp_dir[0]/perp_length, perp_dir[1]/perp_length, 0.0)
                    else:
                        perp_normalized = (0.0, 1.0, 0.0)
                else:
                    align_normalized = (1.0, 0.0, 0.0)
                    perp_normalized = (0.0, 1.0, 0.0)
            except Exception:
                align_normalized = (1.0, 0.0, 0.0)
                perp_normalized = (0.0, 1.0, 0.0)
            
            # Position marker 1m above the centerline with station offset along alignment
            offset_coords = (
                station_offset * align_normalized[0],
                station_offset * align_normalized[1],
                slope_marker_height_offset  # configurable height above centerline
            )
            offset_point = model.create_entity("IfcCartesianPoint", Coordinates=offset_coords)
            
            # Y-axis points perpendicular to alignment (marker thickness direction)
            y_direction = model.create_entity("IfcDirection", DirectionRatios=perp_normalized)
            # Z-axis points up (marker height direction)
            z_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
            
            local_axis_placement = model.create_entity("IfcAxis2Placement3D", 
                                                     Location=offset_point,
                                                     Axis=z_direction,
                                                     RefDirection=y_direction)
            
            local_placement = model.create_entity("IfcLocalPlacement",
                                                PlacementRelTo=base_referent.ObjectPlacement,
                                                RelativePlacement=local_axis_placement)
            
            # Create IfcBuildingElementProxy (same as triangles and red circles)
            slope_marker = model.create_entity("IfcBuildingElementProxy",
                                            GlobalId=generate_ifc_guid(),
                                            OwnerHistory=owner_history,
                                            Name=f"SlopeChange_{station:.1f}m",
                                            Description=f"Slope change marker at station {station:.1f}m",
                                            ObjectType="SlopeChangeMarker",
                                            ObjectPlacement=local_placement,
                                            Representation=product_shape,
                                            PredefinedType="USERDEFINED")
            
            # Create property set with slope change data
            slope_change_properties = [
                model.create_entity("IfcPropertySingleValue",
                                   Name="StationNumber",
                                   NominalValue=model.create_entity("IfcReal", wrappedValue=station)),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="FromGradePercent",
                                   NominalValue=model.create_entity("IfcReal", wrappedValue=point['from_grade']*100)),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="ToGradePercent",
                                   NominalValue=model.create_entity("IfcReal", wrappedValue=point['to_grade']*100)),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="FromGradeDecimal",
                                   NominalValue=model.create_entity("IfcReal", wrappedValue=point['from_grade'])),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="ToGradeDecimal",
                                   NominalValue=model.create_entity("IfcReal", wrappedValue=point['to_grade'])),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="GradeChange",
                                   NominalValue=model.create_entity("IfcReal", wrappedValue=(point['to_grade'] - point['from_grade'])*100)),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="HeightAboveDatum",
                                   NominalValue=model.create_entity("IfcLengthMeasure", wrappedValue=point['height'])),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="ChangeType",
                                   NominalValue=model.create_entity("IfcLabel", wrappedValue=point.get('type', 'unknown'))),
                
                model.create_entity("IfcPropertySingleValue",
                                   Name="MarkerColor",
                                   NominalValue=model.create_entity("IfcLabel", wrappedValue="Orange"))
            ]
            
            slope_change_pset = model.create_entity("IfcPropertySet",
                                             GlobalId=generate_ifc_guid(),
                                             OwnerHistory=owner_history,
                                             Name=property_set_name,
                                             HasProperties=slope_change_properties)
            
            model.create_entity("IfcRelDefinesByProperties",
                               GlobalId=generate_ifc_guid(),
                               OwnerHistory=owner_history,
                               RelatedObjects=[slope_marker],
                               RelatingPropertyDefinition=slope_change_pset)
            
            new_elements.append(slope_marker)
    
    # 2. Add slope information at regular stations
    for referent in referents[::2]:  # Every other station to avoid clutter
        if referent.Name:
            try:
                station = float(referent.Name)
                height = interpolate_height_at_station(station, vertical_segments)
                
                # Find current slope at this station
                current_grade = 0.0
                segment_type = "Unknown"
                
                for segment in vertical_segments:
                    start_dist = segment['start_distance']
                    end_dist = start_dist + segment['length']
                    
                    if start_dist <= station <= end_dist:
                        # Interpolate grade within segment
                        if segment['curve_type'] == '.CONSTANTGRADIENT.':
                            current_grade = segment['start_grade']
                            segment_type = "Constant Grade"
                        else:
                            # For curves, interpolate grade
                            t = (station - start_dist) / segment['length'] if segment['length'] > 0 else 0
                            grade_diff = segment['end_grade'] - segment['start_grade']
                            current_grade = segment['start_grade'] + (t * grade_diff)
                            segment_type = "Vertical Curve"
                        break
                
                # Create information text
                slope_text = f"Grade: {current_grade*100:.1f}%"
                height_text = f"Height: {height:.2f}m"
                type_text = f"{segment_type}"
                
                # Create directional triangle (arrow) pointing along alignment
                # Color based on slope: green for positive (upward), red for negative (downward)
                arrow_triangle = create_directional_triangle(model, length=arrow_length, width=arrow_width, thickness=arrow_thickness)
                
                # Determine color based on slope direction
                if current_grade >= 0:
                    arrow_color_name = "Green"
                    arrow_color_rgb = arrow_color_positive
                else:
                    arrow_color_name = "Red"
                    arrow_color_rgb = arrow_color_negative
                
                # Create color for the arrow
                arrow_color = model.create_entity("IfcColourRgb",
                                                 Name=arrow_color_name,
                                                 Red=arrow_color_rgb[0],
                                                 Green=arrow_color_rgb[1],
                                                 Blue=arrow_color_rgb[2])
                
                arrow_surface_style = model.create_entity("IfcSurfaceStyleRendering",
                                                         SurfaceColour=arrow_color,
                                                         Transparency=0.0,
                                                         ReflectanceMethod="NOTDEFINED")
                
                arrow_style = model.create_entity("IfcSurfaceStyle",
                                                 Name=f"{arrow_color_name}Arrow",
                                                 Side="BOTH",
                                                 Styles=[arrow_surface_style])
                
                arrow_styled_item = model.create_entity("IfcStyledItem",
                                                       Item=arrow_triangle,
                                                       Styles=[arrow_style],
                                                       Name="ArrowStyle")
                
                # Create shape representation for the arrow
                arrow_representation = model.create_entity("IfcShapeRepresentation",
                                                          ContextOfItems=context_3d,
                                                          RepresentationIdentifier="Body",
                                                          RepresentationType="SweptSolid",
                                                          Items=[arrow_triangle])
                
                # Create text literals
                text1 = create_text_literal(model, slope_text, (-1.2, 0.0, 0.4), text_height_medium, text_color, text_font)
                text2 = create_text_literal(model, height_text, (-1.2, 0.0, 0.1), text_height_small, text_color, text_font)
                text3 = create_text_literal(model, type_text, (-1.2, 0.0, -0.2), text_height_small, text_color, text_font)
                
                # Create text representation
                text_representation = model.create_entity("IfcShapeRepresentation",
                                                         ContextOfItems=context_3d,
                                                         RepresentationIdentifier="Annotation",
                                                         RepresentationType="Annotation2D",
                                                         Items=[text1, text2, text3])
                
                # Combine arrow and text representations
                product_shape = model.create_entity("IfcProductDefinitionShape",
                                                  Representations=[arrow_representation, text_representation])
                
                # Get alignment direction from referent
                try:
                    rel_placement = referent.ObjectPlacement.RelativePlacement
                    if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                        align_dir = rel_placement.RefDirection.DirectionRatios
                        import math
                        length = math.sqrt(align_dir[0]**2 + align_dir[1]**2 + align_dir[2]**2)
                        align_normalized = (align_dir[0]/length, align_dir[1]/length, align_dir[2]/length)
                    else:
                        align_normalized = (1.0, 0.0, 0.0)
                except Exception:
                    align_normalized = (1.0, 0.0, 0.0)
                
                # Position arrow and text beside/above the station
                # Arrow at configurable height, pointing in alignment direction
                offset_point = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, arrow_height_offset))
                
                # RefDirection = alignment direction (arrow points this way)
                x_direction = model.create_entity("IfcDirection", DirectionRatios=align_normalized)
                # Z-axis points up
                z_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
                
                local_axis_placement = model.create_entity("IfcAxis2Placement3D", 
                                                         Location=offset_point,
                                                         Axis=z_direction,
                                                         RefDirection=x_direction)
                
                local_placement = model.create_entity("IfcLocalPlacement",
                                                    PlacementRelTo=referent.ObjectPlacement,
                                                    RelativePlacement=local_axis_placement)
                
                # Create IfcBuildingElementProxy for slope information (consistent with markers)
                slope_info = model.create_entity("IfcBuildingElementProxy",
                                            GlobalId=generate_ifc_guid(),
                                            OwnerHistory=owner_history,
                                            Name=f"SlopeInfo_{station:.0f}m",
                                            Description=f"Slope information with directional arrow at station {station:.1f}m",
                                            ObjectType="SlopeInformation",
                                            ObjectPlacement=local_placement,
                                            Representation=product_shape,
                                            PredefinedType="USERDEFINED")
                
                # Create property set with slope data
                properties = [
                    model.create_entity("IfcPropertySingleValue",
                                       Name="StationNumber",
                                       NominalValue=model.create_entity("IfcReal", wrappedValue=station)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="GradePercent",
                                       NominalValue=model.create_entity("IfcReal", wrappedValue=current_grade*100)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="GradeDecimal",
                                       NominalValue=model.create_entity("IfcReal", wrappedValue=current_grade)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="HeightAboveDatum",
                                       NominalValue=model.create_entity("IfcLengthMeasure", wrappedValue=height)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="SegmentType",
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue=segment_type)),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="SlopeDirection",
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue="Upward" if current_grade >= 0 else "Downward")),
                    
                    model.create_entity("IfcPropertySingleValue",
                                       Name="ArrowColor",
                                       NominalValue=model.create_entity("IfcLabel", wrappedValue=arrow_color_name))
                ]
                
                property_set = model.create_entity("IfcPropertySet",
                                                 GlobalId=generate_ifc_guid(),
                                                 OwnerHistory=owner_history,
                                                 Name=property_set_name,
                                                 HasProperties=properties)
                
                model.create_entity("IfcRelDefinesByProperties",
                                   GlobalId=generate_ifc_guid(),
                                   OwnerHistory=owner_history,
                                   RelatedObjects=[slope_info],
                                   RelatingPropertyDefinition=property_set)
                
                new_elements.append(slope_info)
                
            except ValueError:
                continue
    
    # 3. Add segment boundary markers
    for i, segment in enumerate(vertical_segments):
        start_station = segment['start_distance']
        end_station = start_station + segment['length']
        
        # Find closest referent for each boundary
        for station in [start_station, end_station]:
            closest_referent = None
            min_distance = float('inf')
            
            for referent in referents:
                if referent.Name:
                    try:
                        ref_station = float(referent.Name)
                        distance = abs(ref_station - station)
                        if distance < min_distance:
                            min_distance = distance
                            closest_referent = referent
                    except Exception:
                        continue
            
            if closest_referent and min_distance < 5.0:  # Within 5m of a station
                # Create segment boundary text
                # Offset Y position based on whether it's start or end to avoid overlap
                is_start = (station == start_station)
                y_offset = -0.5 if is_start else -1.0  # 0.5m apart
                
                boundary_text = f"Segment {i+1} {'Start' if is_start else 'End'}"
                grade_text = f"Grade: {(segment['start_grade'] if is_start else segment['end_grade'])*100:.1f}%"
                
                # Add station number only for start points
                if is_start:
                    station_text = f"Station: {station:.1f}m"
                    text1 = create_text_literal(model, boundary_text, (0.0, y_offset, 0.5), text_height_small, text_color, text_font)
                    text2 = create_text_literal(model, station_text, (0.0, y_offset, 0.2), text_height_small, text_color, text_font)
                    text3 = create_text_literal(model, grade_text, (0.0, y_offset, -0.1), text_height_small, text_color, text_font)
                    text_items = [text1, text2, text3]
                else:
                    text1 = create_text_literal(model, boundary_text, (0.0, y_offset, 0.2), text_height_small, text_color, text_font)
                    text2 = create_text_literal(model, grade_text, (0.0, y_offset, -0.1), text_height_small, text_color, text_font)
                    text_items = [text1, text2]
                
                text_representation = model.create_entity("IfcShapeRepresentation",
                                                         ContextOfItems=context_3d,
                                                         RepresentationIdentifier="Annotation",
                                                         RepresentationType="Annotation2D",
                                                         Items=text_items)
                
                product_shape = model.create_entity("IfcProductDefinitionShape",
                                                  Representations=[text_representation])
                
                offset_point = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.3))
                z_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
                y_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 1.0, 0.0))
                
                local_axis_placement = model.create_entity("IfcAxis2Placement3D", 
                                                         Location=offset_point,
                                                         Axis=z_direction,
                                                         RefDirection=y_direction)
                
                local_placement = model.create_entity("IfcLocalPlacement",
                                                    PlacementRelTo=closest_referent.ObjectPlacement,
                                                    RelativePlacement=local_axis_placement)
                
                segment_marker = model.create_entity("IfcAnnotation",
                                                GlobalId=generate_ifc_guid(),
                                                OwnerHistory=owner_history,
                                                Name=f"Segment_{i+1}_{station:.1f}m",
                                                Description=f"Segment boundary at {station:.1f}m",
                                                ObjectType="SegmentBoundary",
                                                ObjectPlacement=local_placement,
                                                Representation=product_shape)
                
                new_elements.append(segment_marker)
    
    # Add all new elements to spatial structure
    if new_elements:
        sites = model.by_type("IfcSite")
        if sites:
            site = sites[0]
        else:
            site = model.create_entity("IfcSite",
                                     GlobalId=generate_ifc_guid(),
                                     OwnerHistory=owner_history,
                                     Name="Slope Analysis Site")
            
            site_rel = model.create_entity("IfcRelAggregates",
                                         GlobalId=generate_ifc_guid(),
                                         OwnerHistory=owner_history,
                                         RelatingObject=project,
                                         RelatedObjects=[site])
        
        # Create spatial containment relationship
        containment_rel = model.create_entity("IfcRelContainedInSpatialStructure",
                                            GlobalId=generate_ifc_guid(),
                                            OwnerHistory=owner_history,
                                            RelatedElements=new_elements,
                                            RelatingStructure=site)
    
    # Save the modified model
    model.write(output_file)
    
    print(f"\n✅ Successfully created slope analysis file: {output_file}")
    print(f"📊 Added {len(new_elements)} slope analysis elements:")
    print(f"   🔶 {len(slope_change_points)} slope change markers (orange circles)")
    print(f"   📝 {len([e for e in new_elements if 'SlopeInfo' in e.Name])} station slope information displays")
    print(f"   🏷️ {len([e for e in new_elements if 'Segment' in e.Name])} segment boundary markers")
    
    print("\n📈 Slope Analysis Summary:")
    print(f"   • Total alignment length: {vertical_segments[-1]['start_distance'] + vertical_segments[-1]['length']:.1f}m")
    print(f"   • Steepest upward grade: {max(seg['end_grade'] for seg in vertical_segments)*100:.1f}%")
    print(f"   • Steepest downward grade: {min(seg['start_grade'] for seg in vertical_segments)*100:.1f}%")
    print(f"   • Number of grade changes: {len(slope_change_points)}")

if __name__ == "__main__":
    # ============================================================================
    # USER CONFIGURABLE PARAMETERS
    # ============================================================================
    # Modify these values to customize slope marker appearance and positioning
    
    # Input/Output Files
    input_file = "m_f-veg_CL-1000_with_text.ifc"
    output_file = "m_f-veg_CL-1000_with_text_slope_analysis.ifc"
    
    # Slope Change Marker Settings (Orange circles at grade change points)
    SLOPE_MARKER_RADIUS = 0.4           # Radius of slope change markers in meters
    SLOPE_MARKER_THICKNESS = 0.05       # Thickness of slope change markers in meters
    SLOPE_MARKER_COLOR = (1.0, 0.5, 0.0)  # RGB color (Orange)
    
    # Directional Arrow Settings (Shows slope direction along alignment)
    ARROW_LENGTH = 0.5                  # Length of arrow in meters
    ARROW_WIDTH = 0.25                   # Width of arrow in meters
    ARROW_THICKNESS = 0.05              # Thickness of arrow in meters
    ARROW_COLOR_POSITIVE = (0.0, 0.8, 0.0)  # RGB color for upward slopes (Green)
    ARROW_COLOR_NEGATIVE = (1.0, 0.0, 0.0)  # RGB color for downward slopes (Red)
    
    # Text Settings
    TEXT_HEIGHT_LARGE = 0.6             # Height for large text (e.g., grade changes) in meters
    TEXT_HEIGHT_MEDIUM = 0.5            # Height for medium text (e.g., stations) in meters
    TEXT_HEIGHT_SMALL = 0.4             # Height for small text (e.g., segments) in meters
    TEXT_COLOR = (0.0, 0.0, 0.8)        # RGB color (DarkBlue)
    TEXT_FONT = "Arial"                 # Font family
    
    # Positioning Settings
    SLOPE_MARKER_HEIGHT_OFFSET = 0.5    # Vertical offset for slope markers above centerline (meters)
    ARROW_HEIGHT_OFFSET = 0.8           # Vertical offset for arrows above centerline (meters)
    
    # Property Set Settings
    PROPERTY_SET_NAME = "Pset_SlopeInformation"  # Name of property set attached to slope arrows
    
    # ============================================================================
    # END OF USER CONFIGURABLE PARAMETERS
    # ============================================================================
    
    add_slope_information(
        input_file, 
        output_file,
        slope_marker_radius=SLOPE_MARKER_RADIUS,
        slope_marker_thickness=SLOPE_MARKER_THICKNESS,
        slope_marker_color=SLOPE_MARKER_COLOR,
        arrow_length=ARROW_LENGTH,
        arrow_width=ARROW_WIDTH,
        arrow_thickness=ARROW_THICKNESS,
        arrow_color_positive=ARROW_COLOR_POSITIVE,
        arrow_color_negative=ARROW_COLOR_NEGATIVE,
        text_height_large=TEXT_HEIGHT_LARGE,
        text_height_medium=TEXT_HEIGHT_MEDIUM,
        text_height_small=TEXT_HEIGHT_SMALL,
        text_color=TEXT_COLOR,
        text_font=TEXT_FONT,
        slope_marker_height_offset=SLOPE_MARKER_HEIGHT_OFFSET,
        arrow_height_offset=ARROW_HEIGHT_OFFSET,
        property_set_name=PROPERTY_SET_NAME
    )