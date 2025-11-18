"""
Object-Oriented version of IFC Slope Information Analyzer
Adds slope information, directional arrows, and slope change markers to IFC alignments
"""
import ifcopenshell
import math
from geometry_markers import (
    CircleMarker, DirectionalArrow, MarkerElement,
    generate_ifc_guid
)


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
        list : List of slope change point dictionaries with:
            - station: float (station location)
            - from_grade: float (grade before change)
            - to_grade: float (grade after change)
            - height: float (elevation at change point)
            - type: str ('curve' or 'transition')
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
                    station = segment['start_distance']
                    height = self._calculate_height_at_station(station)
                    
                    slope_changes.append({
                        'station': station,
                        'from_grade': prev_end_grade,
                        'to_grade': current_start_grade,
                        'height': height,
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
                    return start_height + (distance_into_segment * start_grade)
                else:
                    # Parabolic interpolation for curves
                    if length > 0:
                        t = distance_into_segment / length
                        grade_change = end_grade - start_grade
                        current_grade = start_grade + (grade_change * t)
                        return start_height + (distance_into_segment * (start_grade + current_grade) / 2)
                    return start_height
        
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


class TextLiteralCreator:
    """Creates IfcTextLiteral annotations"""
    
    def __init__(self, model):
        """
        Initialize text creator
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        """
        self.model = model
        
    def create_text_literal(self, text_content, position, height=0.4,
                          color=(0.0, 0.0, 0.8), font="Arial", weight="bold"):
        """
        Create IfcTextLiteral with styling
        
        Parameters:
        -----------
        text_content : str
            Text to display
        position : tuple
            XYZ coordinates
        height : float
            Text height in meters
        color : tuple
            RGB color
        font : str
            Font family
        weight : str
            Font weight (normal/bold)
            
        Returns:
        --------
        IfcTextLiteral
        """
        # Create text placement
        text_position = self.model.create_entity("IfcCartesianPoint", Coordinates=position)
        text_axis = self.model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
        text_ref_direction = self.model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
        text_placement = self.model.create_entity(
            "IfcAxis2Placement3D",
            Location=text_position,
            Axis=text_axis,
            RefDirection=text_ref_direction
        )
        
        # Create IfcTextLiteral
        text_literal = self.model.create_entity(
            "IfcTextLiteral",
            Literal=text_content,
            Placement=text_placement,
            Path="RIGHT"
        )
        
        # Create text style
        text_color = self.model.create_entity(
            "IfcColourRgb",
            Name="TextColor",
            Red=color[0],
            Green=color[1],
            Blue=color[2]
        )
        
        text_style = self.model.create_entity(
            "IfcTextStyleForDefinedFont",
            Colour=text_color,
            BackgroundColour=None
        )
        
        text_font_style = self.model.create_entity(
            "IfcTextStyleFontModel",
            Name="SlopeFont",
            FontFamily=[font],
            FontStyle="normal",
            FontVariant="normal",
            FontWeight=weight,
            FontSize=self.model.create_entity("IfcLengthMeasure", wrappedValue=height)
        )
        
        # Create IfcTextStyle
        ifc_text_style = self.model.create_entity(
            "IfcTextStyle",
            Name="SlopeTextStyle",
            TextCharacterAppearance=text_style,
            TextFontStyle=text_font_style
        )
        
        # Apply style
        self.model.create_entity(
            "IfcStyledItem",
            Item=text_literal,
            Styles=[ifc_text_style],
            Name="SlopeTextStyle"
        )
        
        return text_literal


class PlacementCalculator:
    """Utility class for spatial calculations"""
    
    @staticmethod
    def calculate_perpendicular_direction(placement):
        """Calculate perpendicular direction from placement"""
        try:
            rel_placement = placement.RelativePlacement
            if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                align_dir = rel_placement.RefDirection.DirectionRatios
                length = math.sqrt(align_dir[0]**2 + align_dir[1]**2 + align_dir[2]**2)
                align_normalized = (align_dir[0]/length, align_dir[1]/length, align_dir[2]/length)
                
                perp_dir = (-align_normalized[1], align_normalized[0], 0.0)
                perp_length = math.sqrt(perp_dir[0]**2 + perp_dir[1]**2)
                
                if perp_length > 0.001:
                    return (perp_dir[0]/perp_length, perp_dir[1]/perp_length, 0.0)
        except:
            pass
        
        return (1.0, 0.0, 0.0)
    
    @staticmethod
    def extract_position(placement):
        """Extract XYZ position from placement"""
        try:
            rel_placement = placement.RelativePlacement
            location = rel_placement.Location.Coordinates
            return location
        except:
            return (0.0, 0.0, 0.0)
    
    @staticmethod
    def create_offset_placement(model, base_placement, offset_vector):
        """
        Create new placement offset from base placement
        
        Parameters:
        -----------
        model : ifcopenshell.file
            IFC model
        base_placement : IfcLocalPlacement
            Base placement to offset from
        offset_vector : tuple
            XYZ offset vector
            
        Returns:
        --------
        IfcLocalPlacement
        """
        base_pos = PlacementCalculator.extract_position(base_placement)
        new_pos = (
            base_pos[0] + offset_vector[0],
            base_pos[1] + offset_vector[1],
            base_pos[2] + offset_vector[2]
        )
        
        new_location = model.create_entity("IfcCartesianPoint", Coordinates=new_pos)
        
        try:
            base_rel = base_placement.RelativePlacement
            axis = base_rel.Axis if hasattr(base_rel, 'Axis') and base_rel.Axis else None
            ref_dir = base_rel.RefDirection if hasattr(base_rel, 'RefDirection') and base_rel.RefDirection else None
            
            new_rel_placement = model.create_entity(
                "IfcAxis2Placement3D",
                Location=new_location,
                Axis=axis,
                RefDirection=ref_dir
            )
        except:
            new_rel_placement = model.create_entity(
                "IfcAxis2Placement3D",
                Location=new_location
            )
        
        return model.create_entity(
            "IfcLocalPlacement",
            PlacementRelTo=base_placement.PlacementRelTo,
            RelativePlacement=new_rel_placement
        )


class SlopeAnalysisProcessor:
    """Main processor for adding slope analysis to IFC file"""
    
    def __init__(self, model):
        """
        Initialize processor
        
        Parameters:
        -----------
        model : ifcopenshell.file
            The IFC model
        """
        self.model = model
        self.owner_history = model.by_type("IfcOwnerHistory")[0]
        self.context_3d = self._get_3d_context()
        self.slope_factory = SlopeMarkerFactory(model, self.owner_history, self.context_3d)
        self.text_creator = TextLiteralCreator(model)
        
    def _get_3d_context(self):
        """Get 3D geometric representation context"""
        contexts = self.model.by_type("IfcGeometricRepresentationContext")
        for context in contexts:
            if hasattr(context, 'ContextType') and context.ContextType == '3D':
                return context
        return contexts[0] if contexts else None
    
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
                    for segment in rel.RelatedObjects:
                        if segment.is_a("IfcAlignmentVerticalSegment"):
                            design_params = segment.DesignParameters
                            vertical_segments.append({
                                'start_distance': design_params.StartDistAlong,
                                'length': design_params.HorizontalLength,
                                'start_height': design_params.StartHeight,
                                'start_grade': design_params.StartGradient,
                                'end_grade': getattr(design_params, 'EndGradient', design_params.StartGradient),
                                'curve_type': segment.PredefinedType
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
                    station = float(ref.Name)
                    referent_map[station] = ref
                except:
                    pass
        
        return referent_map
    
    def process_slope_changes(self, slope_changes, referent_map, config):
        """
        Create markers and text for slope change points
        
        Parameters:
        -----------
        slope_changes : list
            List of slope change dictionaries
        referent_map : dict
            Station to referent mapping
        config : dict
            Configuration parameters
            
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
            perp_dir = PlacementCalculator.calculate_perpendicular_direction(
                base_referent.ObjectPlacement
            )
            offset = config['slope_marker_height_offset']
            offset_vector = (
                perp_dir[0] * offset,
                perp_dir[1] * offset,
                perp_dir[2] * offset
            )
            
            marker_placement = PlacementCalculator.create_offset_placement(
                self.model,
                base_referent.ObjectPlacement,
                offset_vector
            )
            
            # Create slope change marker
            marker_element = self.slope_factory.create_slope_change_marker(
                change,
                radius=config['slope_marker_radius'],
                thickness=config['slope_marker_thickness'],
                color=config['slope_marker_color'],
                pset_name=config['property_set_name']
            )
            
            element = marker_element.create_ifc_element(
                name=f"SlopeChange_{station:.1f}",
                description=f"Slope change at station {station:.1f}m",
                placement=marker_placement,
                color_name="Orange",
                pset_name=config['property_set_name']
            )
            
            elements.append(element)
            
            # Create text annotations
            base_pos = PlacementCalculator.extract_position(marker_placement)
            
            # Title text
            title_pos = (base_pos[0], base_pos[1] - 0.2, base_pos[2] + 1.2)
            title_text = self.text_creator.create_text_literal(
                f"Slope Change at {station:.1f}m",
                title_pos,
                height=config['text_height_large'],
                color=config['text_color'],
                font=config['text_font']
            )
            
            # Grade change text
            grade_change = (change['to_grade'] - change['from_grade']) * 100
            grade_pos = (base_pos[0], base_pos[1] - 0.2, base_pos[2] + 0.8)
            grade_text = self.text_creator.create_text_literal(
                f"Grade: {change['from_grade']*100:.1f}% → {change['to_grade']*100:.1f}% ({grade_change:+.1f}%)",
                grade_pos,
                height=config['text_height_medium'],
                color=config['text_color'],
                font=config['text_font']
            )
            
        return elements
    
    def process_station_slopes(self, referent_map, vertical_segments, config):
        """
        Create directional arrows at regular stations
        
        Parameters:
        -----------
        referent_map : dict
            Station to referent mapping
        vertical_segments : list
            Vertical alignment segments
        config : dict
            Configuration parameters
            
        Returns:
        --------
        list : Created IFC elements
        """
        elements = []
        detector = SlopeChangeDetector(vertical_segments)
        
        # Process every other station
        stations = sorted(referent_map.keys())
        for i, station in enumerate(stations[::2]):
            referent = referent_map[station]
            
            if not referent.ObjectPlacement:
                continue
            
            # Calculate grade at this station
            grade = self._get_grade_at_station(station, vertical_segments)
            height = detector._calculate_height_at_station(station)
            
            # Create offset placement
            perp_dir = PlacementCalculator.calculate_perpendicular_direction(
                referent.ObjectPlacement
            )
            offset = config['arrow_height_offset']
            offset_vector = (
                perp_dir[0] * offset,
                perp_dir[1] * offset,
                perp_dir[2] * offset
            )
            
            arrow_placement = PlacementCalculator.create_offset_placement(
                self.model,
                referent.ObjectPlacement,
                offset_vector
            )
            
            # Create directional arrow
            is_upward = grade >= 0
            marker_element = self.slope_factory.create_directional_arrow(
                station,
                grade,
                height,
                is_upward=is_upward,
                length=config['arrow_length'],
                width=config['arrow_width'],
                thickness=config['arrow_thickness'],
                segment_type="intermediate",
                pset_name=config['property_set_name']
            )
            
            color_name = "Green" if is_upward else "Red"
            element = marker_element.create_ifc_element(
                name=f"SlopeInfo_{station:.1f}",
                description=f"Slope information at station {station:.1f}m",
                placement=arrow_placement,
                color_name=color_name,
                pset_name=config['property_set_name']
            )
            
            elements.append(element)
            
            # Create text annotation
            base_pos = PlacementCalculator.extract_position(arrow_placement)
            text_pos = (base_pos[0], base_pos[1] - 0.2, base_pos[2] + 0.6)
            
            slope_text = self.text_creator.create_text_literal(
                f"Grade: {grade*100:.1f}%",
                text_pos,
                height=config['text_height_medium'],
                color=config['text_color'],
                font=config['text_font']
            )
            
        return elements
    
    def process_segment_boundaries(self, vertical_segments, referent_map, config):
        """
        Create markers at segment boundaries
        
        Parameters:
        -----------
        vertical_segments : list
            Vertical alignment segments
        referent_map : dict
            Station to referent mapping
        config : dict
            Configuration parameters
            
        Returns:
        --------
        list : Created IFC elements
        """
        elements = []
        
        for i, segment in enumerate(vertical_segments):
            start_station = segment['start_distance']
            end_station = start_station + segment['length']
            
            for station, label_type in [(start_station, "start"), (end_station, "end")]:
                # Find nearest referent
                nearest_station = min(referent_map.keys(),
                                    key=lambda s: abs(s - station),
                                    default=None)
                
                if nearest_station is None or abs(nearest_station - station) > 5.0:
                    continue
                
                referent = referent_map[nearest_station]
                if not referent.ObjectPlacement:
                    continue
                
                base_pos = PlacementCalculator.extract_position(referent.ObjectPlacement)
                
                # Offset text slightly based on start/end
                y_offset = -0.5 if label_type == "start" else -1.0
                text_pos = (base_pos[0], base_pos[1] + y_offset, base_pos[2] + 0.3)
                
                segment_type = "Segment Start" if label_type == "start" else "Segment End"
                label_text = f"{segment_type} - Seg {i+1}"
                
                text_literal = self.text_creator.create_text_literal(
                    label_text,
                    text_pos,
                    height=config['text_height_small'],
                    color=config['text_color'],
                    font=config['text_font']
                )
        
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
                    # Interpolate grade in curve
                    if length > 0:
                        t = (station - start_dist) / length
                        return segment['start_grade'] + t * (segment['end_grade'] - segment['start_grade'])
                    return segment['start_grade']
        
        # Use last segment grade if beyond alignment
        if vertical_segments:
            return vertical_segments[-1]['end_grade']
        return 0.0
    
    def add_to_spatial_structure(self, elements):
        """
        Add elements to IFC spatial structure
        
        Parameters:
        -----------
        elements : list
            List of IFC elements to add
        """
        if not elements:
            return
        
        sites = self.model.by_type("IfcSite")
        if sites:
            site = sites[0]
        else:
            project = self.model.by_type("IfcProject")[0]
            site = self.model.create_entity(
                "IfcSite",
                GlobalId=generate_ifc_guid(),
                OwnerHistory=self.owner_history,
                Name="Slope Analysis Site"
            )
            
            self.model.create_entity(
                "IfcRelAggregates",
                GlobalId=generate_ifc_guid(),
                OwnerHistory=self.owner_history,
                RelatingObject=project,
                RelatedObjects=[site]
            )
        
        self.model.create_entity(
            "IfcRelContainedInSpatialStructure",
            GlobalId=generate_ifc_guid(),
            OwnerHistory=self.owner_history,
            RelatedElements=elements,
            RelatingStructure=site
        )
    
    def print_summary(self, vertical_segments, slope_changes, element_counts):
        """Print processing summary"""
        print(f"\n✅ Successfully created slope analysis file")
        print(f"📊 Added {sum(element_counts.values())} slope analysis elements:")
        print(f"   🔶 {element_counts.get('slope_changes', 0)} slope change markers (orange circles)")
        print(f"   📝 {element_counts.get('station_slopes', 0)} station slope information displays")
        print(f"   🏷️ {element_counts.get('segment_boundaries', 0)} segment boundary markers")
        
        print("\n📈 Slope Analysis Summary:")
        total_length = vertical_segments[-1]['start_distance'] + vertical_segments[-1]['length']
        print(f"   • Total alignment length: {total_length:.1f}m")
        print(f"   • Steepest upward grade: {max(seg['end_grade'] for seg in vertical_segments)*100:.1f}%")
        print(f"   • Steepest downward grade: {min(seg['start_grade'] for seg in vertical_segments)*100:.1f}%")
        print(f"   • Number of grade changes: {len(slope_changes)}")


def add_slope_information_oop(input_file, output_file, config=None):
    """
    Add slope information to IFC alignment using OOP architecture
    
    Parameters:
    -----------
    input_file : str
        Path to input IFC file
    output_file : str
        Path to output IFC file
    config : dict, optional
        Configuration dictionary with parameters
    """
    # Default configuration
    default_config = {
        'slope_marker_radius': 0.4,
        'slope_marker_thickness': 0.05,
        'slope_marker_color': (1.0, 0.5, 0.0),
        'slope_marker_height_offset': 0.5,
        'arrow_length': 0.5,
        'arrow_width': 0.25,
        'arrow_thickness': 0.05,
        'arrow_height_offset': 0.8,
        'text_height_large': 0.6,
        'text_height_medium': 0.5,
        'text_height_small': 0.4,
        'text_color': (0.0, 0.0, 0.8),
        'text_font': "Arial",
        'property_set_name': "Pset_SlopeInformation",
        'grade_change_threshold': 0.01
    }
    
    # Merge with user config
    if config:
        default_config.update(config)
    config = default_config
    
    # Open IFC file
    model = ifcopenshell.open(input_file)
    
    # Initialize processor
    processor = SlopeAnalysisProcessor(model)
    
    # Extract data
    vertical_segments = processor.extract_vertical_segments()
    referent_map = processor.build_referent_map()
    
    print(f"Found {len(vertical_segments)} vertical segments")
    print(f"Found {len(referent_map)} station referents")
    
    # Detect slope changes
    detector = SlopeChangeDetector(vertical_segments, config['grade_change_threshold'])
    slope_changes = detector.detect_slope_changes()
    
    # Add known changes (optional)
    known_changes = [
        {'station': 28.36, 'from_grade': -0.03, 'to_grade': 0.0202, 'height': 2.93, 'type': 'known'},
        {'station': 106.86, 'from_grade': 0.0202, 'to_grade': -0.04, 'height': 3.63, 'type': 'known'},
        {'station': 192.91, 'from_grade': -0.04, 'to_grade': 0.011, 'height': 1.82, 'type': 'known'}
    ]
    slope_changes = detector.add_known_changes(slope_changes, known_changes)
    
    print(f"Identified {len(slope_changes)} slope change points")
    
    # Process and create elements
    all_elements = []
    element_counts = {}
    
    # Slope change markers
    slope_change_elements = processor.process_slope_changes(slope_changes, referent_map, config)
    all_elements.extend(slope_change_elements)
    element_counts['slope_changes'] = len(slope_change_elements)
    
    # Station slope information
    station_slope_elements = processor.process_station_slopes(referent_map, vertical_segments, config)
    all_elements.extend(station_slope_elements)
    element_counts['station_slopes'] = len(station_slope_elements)
    
    # Segment boundaries
    segment_boundary_elements = processor.process_segment_boundaries(vertical_segments, referent_map, config)
    all_elements.extend(segment_boundary_elements)
    element_counts['segment_boundaries'] = len(segment_boundary_elements)
    
    # Add to spatial structure
    processor.add_to_spatial_structure(all_elements)
    
    # Save model
    model.write(output_file)
    
    # Print summary
    processor.print_summary(vertical_segments, slope_changes, element_counts)
    print(f"\n💾 Saved to: {output_file}")


if __name__ == "__main__":
    # ============================================================================
    # USER CONFIGURABLE PARAMETERS
    # ============================================================================
    
    # Input/Output Files
    input_file = "m_f-veg_CL-1000_with_text_oop.ifc"
    output_file = "m_f-veg_CL-1000_with_text_slope_analysis_oop.ifc"
    
    # Configuration dictionary
    config = {
        # Slope Change Marker Settings (Orange circles)
        'slope_marker_radius': 0.4,
        'slope_marker_thickness': 0.05,
        'slope_marker_color': (1.0, 0.5, 0.0),  # Orange
        'slope_marker_height_offset': 0.5,
        
        # Directional Arrow Settings
        'arrow_length': 0.5,
        'arrow_width': 0.25,
        'arrow_thickness': 0.05,
        'arrow_height_offset': 0.8,
        
        # Text Settings
        'text_height_large': 0.6,
        'text_height_medium': 0.5,
        'text_height_small': 0.4,
        'text_color': (0.0, 0.0, 0.8),  # Dark blue
        'text_font': "Arial",
        
        # Property Set Settings
        'property_set_name': "Pset_SlopeInformation",
        
        # Detection Settings
        'grade_change_threshold': 0.01  # 1% minimum grade change
    }
    
    # ============================================================================
    # END OF USER CONFIGURABLE PARAMETERS
    # ============================================================================
    
    add_slope_information_oop(input_file, output_file, config)
