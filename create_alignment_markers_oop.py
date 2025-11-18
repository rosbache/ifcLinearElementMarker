"""
Object-Oriented IFC Alignment Marker Creator
Creates station markers with text annotations and optional slope analysis
"""
import os
import ifcopenshell
import math
from geometry_markers import (
    TriangleMarker, CircleMarker, DirectionalArrow, MarkerElement, 
    TextAnnotation, generate_ifc_guid
)


# ============================================================================
# STATION MARKER CLASSES
# ============================================================================

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


# ============================================================================
# SLOPE ANALYSIS CLASSES
# ============================================================================

class SlopeChangeDetector:
    """Detects slope change points in vertical alignment segments"""
    
    def __init__(self, vertical_segments, grade_change_threshold=0.01):
        """
        Initialize slope change detector
        
        Parameters:
        -----------
        vertical_segments : list
            List of vertical alignment segment dictionaries
        grade_change_threshold : float
            Minimum grade change to detect (default: 0.01 = 1%)
        """
        self.vertical_segments = sorted(vertical_segments, key=lambda x: x['start_distance'])
        self.grade_change_threshold = grade_change_threshold
        
    def detect_slope_changes(self):
        """
        Detect all slope change points in the alignment
        
        Returns:
        --------
        list : List of slope change point dictionaries
        """
        slope_changes = []
        
        for i, segment in enumerate(self.vertical_segments):
            # Check for grade change within segment (curve)
            if abs(segment['start_grade'] - segment['end_grade']) > self.grade_change_threshold:
                # Slope change at end of curve
                end_station = segment['start_distance'] + segment['length']
                end_height = self._calculate_height_at_station(end_station)
                
                slope_changes.append({
                    'station': end_station,
                    'from_grade': segment['start_grade'],
                    'to_grade': segment['end_grade'],
                    'height': end_height,
                    'type': 'curve'
                })
            
            # Check for grade change between adjacent segments
            if i > 0:
                prev_segment = self.vertical_segments[i-1]
                current_start_grade = segment['start_grade']
                prev_end_grade = prev_segment['end_grade']
                
                if abs(current_start_grade - prev_end_grade) > self.grade_change_threshold:
                    slope_changes.append({
                        'station': segment['start_distance'],
                        'from_grade': prev_end_grade,
                        'to_grade': current_start_grade,
                        'height': segment['start_height'],
                        'type': 'transition'
                    })
        
        return slope_changes
    
    def add_known_changes(self, slope_changes, known_changes):
        """
        Add known slope changes if not already detected
        
        Parameters:
        -----------
        slope_changes : list
            Existing detected slope changes
        known_changes : list
            List of known slope change dictionaries
            
        Returns:
        --------
        list : Combined list of slope changes
        """
        for known in known_changes:
            # Check if already exists
            exists = any(
                abs(existing['station'] - known['station']) < 0.5
                for existing in slope_changes
            )
            
            if not exists:
                slope_changes.append(known)
        
        return sorted(slope_changes, key=lambda x: x['station'])
    
    def _calculate_height_at_station(self, station):
        """Calculate height at specific station"""
        for segment in self.vertical_segments:
            start_dist = segment['start_distance']
            length = segment['length']
            end_dist = start_dist + length
            
            if start_dist <= station <= end_dist:
                distance_into_segment = station - start_dist
                start_height = segment['start_height']
                start_grade = segment['start_grade']
                end_grade = segment['end_grade']
                
                if segment['curve_type'] == '.CONSTANTGRADIENT.':
                    height = start_height + (distance_into_segment * start_grade)
                else:
                    # Parabolic interpolation for curves
                    if length > 0:
                        t = distance_into_segment / length
                        grade_change = end_grade - start_grade
                        current_grade = start_grade + (grade_change * t)
                        height = start_height + (distance_into_segment * (start_grade + current_grade) / 2)
                    else:
                        height = start_height
                
                return height
        
        # Extrapolate from last segment
        if self.vertical_segments:
            last_segment = self.vertical_segments[-1]
            last_station = last_segment['start_distance'] + last_segment['length']
            last_height = last_segment['start_height'] + (last_segment['length'] * last_segment['end_grade'])
            extra_distance = station - last_station
            return last_height + (extra_distance * last_segment['end_grade'])
        
        return 0.0


class SlopeMarkerFactory:
    """Factory for creating slope-related markers"""
    
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
        
    def create_slope_change_marker(self, slope_change, radius=0.4, thickness=0.06,
                                   color=(1.0, 0.5, 0.0), pset_name="Pset_SlopeChange"):
        """
        Create orange circle marker for slope change point
        
        Parameters:
        -----------
        slope_change : dict
            Slope change information
        radius : float
            Marker radius
        thickness : float
            Marker thickness
        color : tuple
            RGB color (default: orange)
        pset_name : str
            Property set name
            
        Returns:
        --------
        MarkerElement
        """
        geometry = CircleMarker(self.model, radius, thickness, color)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Add properties
        grade_change = slope_change['to_grade'] - slope_change['from_grade']
        marker_element.add_properties({
            "StationNumber": slope_change['station'],
            "FromGradePercent": slope_change['from_grade'] * 100,
            "ToGradePercent": slope_change['to_grade'] * 100,
            "FromGradeDecimal": slope_change['from_grade'],
            "ToGradeDecimal": slope_change['to_grade'],
            "GradeChange": grade_change * 100,
            "HeightAboveDatum": slope_change['height'],
            "ChangeType": slope_change['type'],
            "MarkerColor": "Orange"
        })
        
        return marker_element
    
    def create_directional_arrow(self, station, grade, height, is_upward=True,
                                length=0.6, width=0.3, thickness=0.05,
                                segment_type="intermediate", pset_name="Pset_SlopeInformation"):
        """
        Create directional arrow showing slope direction
        
        Parameters:
        -----------
        station : float
            Station number
        grade : float
            Grade value (decimal)
        height : float
            Elevation
        is_upward : bool
            True for positive slope, False for negative
        length : float
            Arrow length
        width : float
            Arrow width
        thickness : float
            Arrow thickness
        segment_type : str
            Type of segment (start, end, intermediate)
        pset_name : str
            Property set name
            
        Returns:
        --------
        MarkerElement
        """
        geometry = DirectionalArrow(self.model, length, width, thickness, is_upward)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Add properties
        marker_element.add_properties({
            "StationNumber": station,
            "GradePercent": grade * 100,
            "GradeDecimal": grade,
            "HeightAboveDatum": height,
            "SegmentType": segment_type,
            "SlopeDirection": "Upward" if is_upward else "Downward",
            "ArrowColor": "Green" if is_upward else "Red"
        })
        
        return marker_element


# ============================================================================
# SHARED UTILITY CLASSES
# ============================================================================

class PlacementCalculator:
    """Utility class for spatial calculations"""
    
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
    
    @staticmethod
    def extract_position(placement):
        """Extract XYZ position from placement"""
        try:
            rel_placement = placement.RelativePlacement
            location = rel_placement.Location.Coordinates
            return location
        except Exception:
            return (0.0, 0.0, 0.0)


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
                                          height=1.0, color=(0.0, 0.0, 0.0), weight="normal"):
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
        weight : str
            Font weight (normal/bold)
            
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
            FontWeight=weight,
            FontSize=self.model.create_entity("IfcLengthMeasure", wrappedValue=height)
        )
        
        ifc_text_style = self.model.create_entity(
            "IfcTextStyle",
            Name="TextStyle",
            TextCharacterAppearance=text_style_char,
            TextFontStyle=text_font_style
        )
        
        # Apply style
        self.model.create_entity(
            "IfcStyledItem",
            Item=text_literal,
            Styles=[ifc_text_style],
            Name="TextStyle"
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


# ============================================================================
# MAIN PROCESSOR CLASS
# ============================================================================

class AlignmentMarkerProcessor:
    """Main processor for creating alignment markers and optional slope analysis"""
    
    def __init__(self, model, config):
        """
        Initialize processor
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        config : dict
            Configuration dictionary with all settings
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
        self.station_factory = StationMarkerFactory(model, self.owner_history, self.context_3d)
        self.slope_factory = SlopeMarkerFactory(model, self.owner_history, self.context_3d)
        self.text_creator = TextLiteralCreator(model, self.context_3d)
        
    def _get_3d_context(self):
        """Get 3D geometric representation context"""
        contexts = self.model.by_type("IfcGeometricRepresentationContext")
        for context in contexts:
            if hasattr(context, 'ContextType') and context.ContextType == '3D':
                return context
        return contexts[0] if contexts else None
    
    def process_station_markers(self):
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
                except Exception:
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
            marker_element = self.station_factory.create_circle_marker(
                station_value,
                placement,
                self.config['circle_radius'],
                self.config['circle_thickness'],
                self.config['circle_color']
            )
        else:
            marker_element = self.station_factory.create_triangle_marker(
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
    
    def extract_vertical_segments(self):
        """
        Extract vertical alignment segments from IFC
        
        Returns:
        --------
        list : List of vertical segment dictionaries
        """
        vertical_segments = []
        alignment_verticals = self.model.by_type("IfcAlignmentVertical")
        
        for vertical in alignment_verticals:
            for rel in self.model.by_type("IfcRelNests"):
                if rel.RelatingObject == vertical:
                    for segment_entity in rel.RelatedObjects:
                        # Handle both IFC 4.3 (DesignParameters) and IFC 4.0 (direct attributes)
                        if hasattr(segment_entity, 'DesignParameters'):
                            # IFC 4.3 format
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
                        elif segment_entity.is_a("IfcAlignmentVerticalSegment"):
                            # IFC 4.0 format - attributes directly on segment
                            if hasattr(segment_entity, 'StartDistAlong') and hasattr(segment_entity, 'HorizontalLength'):
                                vertical_segments.append({
                                    'start_distance': segment_entity.StartDistAlong,
                                    'length': segment_entity.HorizontalLength,
                                    'start_height': segment_entity.StartHeight,
                                    'start_grade': segment_entity.StartGradient,
                                    'end_grade': segment_entity.EndGradient,
                                    'curve_type': str(segment_entity.PredefinedType) if hasattr(segment_entity, 'PredefinedType') else '.CONSTANTGRADIENT.',
                                    'radius': getattr(segment_entity, 'StartRadiusOfCurvature', None)
                                })
        
        return sorted(vertical_segments, key=lambda x: x['start_distance'])
    
    def build_referent_map(self):
        """
        Build map of station values to referent objects
        
        Returns:
        --------
        dict : Station value -> referent object mapping
        """
        referent_map = {}
        referents = self.model.by_type("IfcReferent")
        
        for ref in referents:
            if ref.Name:
                try:
                    station_val = float(ref.Name)
                    referent_map[station_val] = ref
                except Exception:
                    pass
        
        return referent_map
    
    def process_slope_changes(self, slope_changes, referent_map):
        """
        Create markers and text for slope change points
        
        Parameters:
        -----------
        slope_changes : list
            List of slope change dictionaries
        referent_map : dict
            Station to referent mapping
            
        Returns:
        --------
        list : Created IFC elements
        """
        elements = []
        
        for change in slope_changes:
            station = change['station']
            
            # Find nearest referent
            base_referent = referent_map.get(station)
            if not base_referent:
                nearest_station = min(referent_map.keys(), 
                                    key=lambda s: abs(s - station))
                base_referent = referent_map[nearest_station]
            
            if not base_referent or not base_referent.ObjectPlacement:
                continue
            
            # Calculate placement
            offset_height = self.config['slope_marker_height_offset']
            offset_vector = (0.0, 0.0, offset_height)
            
            marker_placement = PlacementCalculator.create_marker_placement(
                self.model,
                base_referent.ObjectPlacement,
                offset_height
            )
            
            # Create slope change marker
            marker_element = self.slope_factory.create_slope_change_marker(
                change,
                radius=self.config['slope_marker_radius'],
                thickness=self.config['slope_marker_thickness'],
                color=self.config['slope_marker_color'],
                pset_name=self.config['property_set_name']
            )
            
            element = marker_element.create_ifc_element(
                name=f"SlopeChange_{station:.1f}",
                description=f"Slope change at station {station:.1f}m",
                placement=marker_placement,
                color_name="Orange",
                pset_name=self.config['property_set_name']
            )
            
            elements.append(element)
        
        return elements
    
    def process_station_slopes(self, referent_map, vertical_segments):
        """
        Create directional arrows at regular stations
        
        Parameters:
        -----------
        referent_map : dict
            Station to referent mapping
        vertical_segments : list
            Vertical alignment segments
            
        Returns:
        --------
        list : Created IFC elements
        """
        elements = []
        detector = SlopeChangeDetector(vertical_segments)
        
        # Process every other station
        stations = sorted(referent_map.keys())
        for station in stations[::2]:
            referent = referent_map[station]
            
            if not referent.ObjectPlacement:
                continue
            
            # Calculate grade at this station
            grade = self._get_grade_at_station(station, vertical_segments)
            height = detector._calculate_height_at_station(station)
            
            # Create offset placement
            offset_height = self.config['arrow_height_offset']
            
            arrow_placement = PlacementCalculator.create_marker_placement(
                self.model,
                referent.ObjectPlacement,
                offset_height
            )
            
            # Create directional arrow
            is_upward = grade >= 0
            marker_element = self.slope_factory.create_directional_arrow(
                station,
                grade,
                height,
                is_upward=is_upward,
                length=self.config['arrow_length'],
                width=self.config['arrow_width'],
                thickness=self.config['arrow_thickness'],
                segment_type="intermediate",
                pset_name=self.config['property_set_name']
            )
            
            color_name = "Green" if is_upward else "Red"
            element = marker_element.create_ifc_element(
                name=f"SlopeInfo_{station:.1f}",
                description=f"Slope information at station {station:.1f}m",
                placement=arrow_placement,
                color_name=color_name,
                pset_name=self.config['property_set_name']
            )
            
            elements.append(element)
        
        return elements
    
    def _get_grade_at_station(self, station, vertical_segments):
        """Calculate grade at specific station"""
        for segment in vertical_segments:
            start_dist = segment['start_distance']
            length = segment['length']
            end_dist = start_dist + length
            
            if start_dist <= station <= end_dist:
                if segment['curve_type'] == '.CONSTANTGRADIENT.':
                    return segment['start_grade']
                else:
                    # Interpolate grade for curves
                    if length > 0:
                        t = (station - start_dist) / length
                        grade_diff = segment['end_grade'] - segment['start_grade']
                        return segment['start_grade'] + (t * grade_diff)
                    return segment['start_grade']
        
        # Use last segment grade if beyond alignment
        if vertical_segments:
            return vertical_segments[-1]['end_grade']
        return 0.0
    
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
                Name="Alignment Marker Site"
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


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def create_alignment_markers(input_file, output_file, add_slope_analysis=True, **config):
    """
    Main function to create alignment markers with optional slope analysis
    
    Parameters:
    -----------
    input_file : str
        Path to input IFC file
    output_file : str
        Path to output IFC file
    add_slope_analysis : bool
        If True, add slope information markers (default: True)
    **config : dict
        Configuration parameters
    """
    # Open IFC file
    model = ifcopenshell.open(input_file)
    
    # Create processor
    processor = AlignmentMarkerProcessor(model, config)
    
    # Process station markers
    print("\n" + "="*60)
    print("CREATING STATION MARKERS")
    print("="*60)
    station_elements = processor.process_station_markers()
    
    all_elements = station_elements
    slope_elements = []
    
    # Process slope analysis if enabled
    if add_slope_analysis:
        print("\n" + "="*60)
        print("ADDING SLOPE ANALYSIS")
        print("="*60)
        
        # Extract vertical segments
        vertical_segments = processor.extract_vertical_segments()
        print(f"Found {len(vertical_segments)} vertical segments")
        
        if vertical_segments:
            # Build referent map
            referent_map = processor.build_referent_map()
            print(f"Found {len(referent_map)} station referents")
            
            # Detect slope changes
            detector = SlopeChangeDetector(vertical_segments, config.get('grade_change_threshold', 0.01))
            slope_changes = detector.detect_slope_changes()
            
            # Add known changes if provided
            if 'known_slope_changes' in config:
                slope_changes = detector.add_known_changes(slope_changes, config['known_slope_changes'])
            
            print(f"Identified {len(slope_changes)} slope change points")
            
            # Create slope markers
            slope_change_elements = processor.process_slope_changes(slope_changes, referent_map)
            station_slope_elements = processor.process_station_slopes(referent_map, vertical_segments)
            
            slope_elements = slope_change_elements + station_slope_elements
            all_elements.extend(slope_elements)
        else:
            print("⚠️  No vertical alignment segments found - skipping slope analysis")
    
    # Add to spatial structure
    processor.add_to_spatial_structure(all_elements)
    
    # Save model
    model.write(output_file)
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Saved IFC file to: {output_file}")
    print(f"\nCreated {len(station_elements)} station marker elements:")
    print(f"  - Start/End stations: RED circular markers ({config['circle_radius']}m radius)")
    print(f"  - Intermediate stations: GREEN triangular markers ({config['triangle_height']}m height)")
    print(f"  - All positioned {config['marker_height_offset']}m above alignment")
    print(f"  - Include {config['text_height']}m tall text labels")
    
    if add_slope_analysis and slope_elements:
        print(f"\nCreated {len(slope_elements)} slope analysis elements:")
        print(f"  - Slope change markers (orange circles): {config['slope_marker_radius']}m radius")
        print(f"  - Directional arrows (green/red): {config['arrow_length']}m length")
        print(f"  - Positioned {config['slope_marker_height_offset']}m and {config['arrow_height_offset']}m above alignment")
    elif add_slope_analysis:
        print("\nSlope analysis was enabled but no vertical alignment data found")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    # ============================================================================
    # USER CONFIGURABLE PARAMETERS
    # ============================================================================
    
    # Input/Output Files
    INPUT_FILE = "m_f-veg_CL-1000.ifc"
    OUTPUT_FILE = "m_f-veg_CL-1000_with_markers.ifc"
    
    # Enable/Disable Slope Analysis
    ADD_SLOPE_ANALYSIS = True  # Set to False to only create station markers
    
    # ============================================================================
    # STATION MARKER SETTINGS
    # ============================================================================
    
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
    # SLOPE ANALYSIS SETTINGS (only used if ADD_SLOPE_ANALYSIS = True)
    # ============================================================================
    
    # Slope Change Marker Settings (Orange circles at grade change points)
    SLOPE_MARKER_RADIUS = 0.4           # Radius of slope change markers in meters
    SLOPE_MARKER_THICKNESS = 0.05       # Thickness of slope change markers in meters
    SLOPE_MARKER_COLOR = (1.0, 0.5, 0.0)  # RGB color (Orange)
    SLOPE_MARKER_HEIGHT_OFFSET = 0.5    # Vertical offset above centerline (meters)
    
    # Directional Arrow Settings (Shows slope direction along alignment)
    ARROW_LENGTH = 0.5                  # Length of arrow in meters
    ARROW_WIDTH = 0.25                  # Width of arrow in meters
    ARROW_THICKNESS = 0.05              # Thickness of arrow in meters
    ARROW_HEIGHT_OFFSET = 0.8           # Vertical offset above centerline (meters)
    
    # Slope Text Settings
    TEXT_HEIGHT_LARGE = 0.6             # Height for large text (e.g., grade changes) in meters
    TEXT_HEIGHT_MEDIUM = 0.5            # Height for medium text (e.g., stations) in meters
    TEXT_HEIGHT_SMALL = 0.4             # Height for small text (e.g., segments) in meters
    TEXT_COLOR_SLOPE = (0.0, 0.0, 0.8)  # RGB color for slope text (DarkBlue)
    TEXT_FONT = "Arial"                 # Font family
    
    # Property Set Settings
    PROPERTY_SET_NAME = "Pset_SlopeInformation"  # Name of property set
    
    # Detection Settings
    GRADE_CHANGE_THRESHOLD = 0.01  # Minimum grade change to detect (1%)
    
    # Known Slope Changes (optional - leave empty list if not needed)
    KNOWN_SLOPE_CHANGES = [
        {'station': 28.36, 'from_grade': -0.03, 'to_grade': 0.0202, 'height': 2.93, 'type': 'known'},
        {'station': 106.86, 'from_grade': 0.0202, 'to_grade': -0.04, 'height': 3.63, 'type': 'known'},
        {'station': 192.91, 'from_grade': -0.04, 'to_grade': 0.011, 'height': 1.82, 'type': 'known'}
    ]
    
    # ============================================================================
    # END OF USER CONFIGURABLE PARAMETERS
    # ============================================================================
    
    # Create configuration dictionary
    config = {
        # Station marker config
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
        'text_position_offset': TEXT_POSITION_OFFSET,
        
        # Slope analysis config
        'slope_marker_radius': SLOPE_MARKER_RADIUS,
        'slope_marker_thickness': SLOPE_MARKER_THICKNESS,
        'slope_marker_color': SLOPE_MARKER_COLOR,
        'slope_marker_height_offset': SLOPE_MARKER_HEIGHT_OFFSET,
        'arrow_length': ARROW_LENGTH,
        'arrow_width': ARROW_WIDTH,
        'arrow_thickness': ARROW_THICKNESS,
        'arrow_height_offset': ARROW_HEIGHT_OFFSET,
        'text_height_large': TEXT_HEIGHT_LARGE,
        'text_height_medium': TEXT_HEIGHT_MEDIUM,
        'text_height_small': TEXT_HEIGHT_SMALL,
        'text_font': TEXT_FONT,
        'property_set_name': PROPERTY_SET_NAME,
        'grade_change_threshold': GRADE_CHANGE_THRESHOLD,
        'known_slope_changes': KNOWN_SLOPE_CHANGES
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
        print(f"Slope analysis: {'ENABLED' if ADD_SLOPE_ANALYSIS else 'DISABLED'}")
        
        create_alignment_markers(INPUT_FILE, OUTPUT_FILE, ADD_SLOPE_ANALYSIS, **config)
        
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
        import traceback
        traceback.print_exc()
        exit(1)
