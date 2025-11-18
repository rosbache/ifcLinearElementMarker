"""
Object-Oriented IFC Alignment Marker Creator

This module provides a comprehensive system for creating station markers and slope analysis
along IFC alignment centerlines. It uses an object-oriented architecture with factory patterns,
shared geometry classes, and modular components.

Main Features:
--------------
- Station markers (triangles and circles) with text labels at referent points
- Optional slope analysis with grade change detection and directional arrows
- Dual text representation (IfcTextLiteral + polyline fallback) for viewer compatibility
- Configurable marker sizes, colors, and positioning
- Property sets with comprehensive metadata

Architecture:
-------------
- Factory Pattern: Centralized marker creation via StationMarkerFactory and SlopeMarkerFactory
- Shared Geometry: Reusable marker classes in geometry_markers.py module
- Utility Classes: PlacementCalculator for spatial calculations, TextLiteralCreator for text
- Main Processor: AlignmentMarkerProcessor orchestrates the entire workflow

Usage:
------
    python create_alignment_markers_oop.py

Configuration:
--------------
All parameters are configurable in the USER CONFIGURABLE PARAMETERS section at the bottom
of this file. Set ADD_SLOPE_ANALYSIS = True/False to enable/disable slope analysis.

Author: AFRY
Date: 2025
"""
import os
import ifcopenshell
import math
from geometry_markers import (
    TriangleMarker, CircleMarker, DirectionalArrow, MarkerElement, 
    TextAnnotation, generate_ifc_guid
)

__author__ = 'Eirik Rosbach'
__copyright__ = 'Copyright 2025, Eirik Rosbach'
__license__ = ""
__version__ = '0.1'
__email__ = 'eirik.rosbach@afry.com'
__status__ = ' Prototype'

# ============================================================================
# STATION MARKER CLASSES
# ============================================================================

class StationMarkerFactory:
    """
    Factory class for creating station markers (triangles and circles).
    
    This factory creates geometric representations and annotation elements for stations
    along an alignment. Each station gets:
    - A triangle marker (green, perpendicular to alignment)
    - A circle marker (red for start/end, green for intermediate stations)
    - Text annotations showing station number, offset distance, and elevation
    
    Attributes:
        model (ifcopenshell.file): The IFC file being modified
        owner_history (IfcOwnerHistory): IFC ownership and history information
        context_3d (IfcGeometricRepresentationContext): The 3D geometric context for shapes
            
    Example:
        >>> factory = StationMarkerFactory(model, owner_history, context_3d)
        >>> triangle = factory.create_triangle_marker(station_value=100.0, placement=...)
    """
    
    def __init__(self, model, owner_history, context_3d):
        """
        Initialize the station marker factory.
        
        Args:
            model (ifcopenshell.file): The IFC file being modified
            owner_history (IfcOwnerHistory): IFC ownership and history information
            context_3d (IfcGeometricRepresentationContext): 3D geometric context for shape representation
        """
        self.model = model
        self.owner_history = owner_history
        self.context_3d = context_3d
        
    def create_triangle_marker(self, station_value, placement, 
                               height=0.5, thickness=0.05, color=(0.0, 0.8, 0.0)):
        """
        Create a triangular marker at a station point.
        
        Triangles mark station locations and are oriented perpendicular to the alignment.
        They use green color to indicate normal station points.
        
        Args:
            station_value (float): Distance along alignment in meters
            placement (IfcLocalPlacement): Spatial placement for the marker (perpendicular to alignment)
            height (float, optional): Height of triangle in meters. Defaults to 0.5m.
            thickness (float, optional): Thickness of triangle in meters. Defaults to 0.05m.
            color (tuple, optional): RGB color values (0-1 range). Defaults to green (0.0, 0.8, 0.0).
            
        Returns:
            IfcAnnotation: The created annotation element with triangle geometry and properties
            
        Implementation:
            - Creates triangle using TriangleMarker from geometry_markers module
            - Applies color via IfcStyledItem
            - Adds property set with station value, marker type, dimensions, and color
            - Returns configured MarkerElement as IfcAnnotation
        """
        geometry = TriangleMarker(self.model, height, thickness, color)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Add property set with marker metadata
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
        """
        Create a circular marker at start/end stations or slope change points.
        
        Circles mark special locations: start of alignment, end of alignment, and slope changes.
        Color indicates the type: red for start/end, orange for slope changes.
        
        Args:
            station_value (float): Distance along alignment in meters
            placement (IfcLocalPlacement): Spatial placement for the marker (perpendicular to alignment)
            radius (float, optional): Radius of circle in meters. Defaults to 0.5m.
            thickness (float, optional): Thickness of circle disk in meters. Defaults to 0.05m.
            color (tuple, optional): RGB color values (0-1 range). Defaults to red (1.0, 0.0, 0.0).
            marker_type (str, optional): Type identifier for properties. Defaults to "End".
            
        Returns:
            IfcAnnotation: The created annotation element with circle geometry and properties
            
        Implementation:
            - Creates circle using CircleMarker from geometry_markers module
            - Applies color via IfcStyledItem
            - Adds property set with station value, marker type, dimensions, and color
            - Returns configured MarkerElement as IfcAnnotation
        """
        geometry = CircleMarker(self.model, radius, thickness, color)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Add property set with marker metadata
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
    """
    Detects slope change points in vertical alignment segments.
    
    This class analyzes the vertical profile of an alignment to identify points where
    the grade (slope) changes significantly. It processes vertical segments (constant
    slope sections) and identifies transitions that exceed a threshold.
    
    The detector performs grade interpolation at referent points to provide accurate
    slope values even when referent points don't align exactly with segment boundaries.
    
    Attributes:
        vertical_segments (list): List of IfcAlignmentVerticalSegment entities
        grade_change_threshold (float): Minimum grade change to detect (decimal, e.g., 0.01 = 1%)
        
    Example:
        >>> detector = SlopeChangeDetector(vertical_segments, grade_change_threshold=0.01)
        >>> changes = detector.detect_slope_changes(referent_data)
        >>> for change in changes:
        ...     print(f"Grade change at {change['station']}: {change['grade_before']} -> {change['grade_after']}")
    """
    
    def __init__(self, vertical_segments, grade_change_threshold=0.01):
        """
        Initialize slope change detector.
        
        Args:
            vertical_segments (list): List of IfcAlignmentVerticalSegment entities from the alignment
            grade_change_threshold (float): Minimum grade change to detect in decimal form
                                           (e.g., 0.01 represents 1% change)
        """
        # Sort segments by distance to ensure proper sequential processing
        self.vertical_segments = sorted(vertical_segments, key=lambda x: x['start_distance'])
        self.grade_change_threshold = grade_change_threshold
        
    def detect_slope_changes(self):
        """
        Detect all slope change points in the alignment.
        
        Analyzes vertical segments to find:
        1. Grade changes within curved segments (parabolic vertical curves)
        2. Grade changes between adjacent segments (transitions)
        
        Returns:
            list: List of slope change dictionaries, each containing:
                - station (float): Distance along alignment in meters
                - from_grade (float): Previous grade in decimal form
                - to_grade (float): New grade in decimal form
                - height (float): Elevation at the change point in meters
                - type (str): Either 'curve' (within segment) or 'transition' (between segments)
                
        Algorithm:
            - For each segment, check if start and end grades differ significantly
            - For adjacent segments, check if end grade of previous differs from start grade of current
            - Only records changes exceeding the threshold to filter noise
        """
        slope_changes = []
        
        for i, segment in enumerate(self.vertical_segments):
            # Check for grade change within segment (parabolic vertical curve)
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
            
            # Check for grade change between adjacent segments (tangent transitions)
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
        Add known slope changes if not already detected.
        
        Merges manually specified slope changes with auto-detected ones, avoiding duplicates.
        Useful for adding important changes that fall below the threshold or for validation.
        
        Args:
            slope_changes (list): List of auto-detected slope changes
            known_changes (list): List of manually specified slope changes with same dictionary structure
            
        Returns:
            list: Combined list with duplicates removed (based on station proximity)
            
        Implementation:
            - Considers changes at the same station (within 0.01m) as duplicates
            - Keeps auto-detected version if duplicate found
        """
        # Add known changes that aren't already detected
        for known in known_changes:
            # Check if a change at this station already exists (within 0.5m tolerance)
            exists = any(
                abs(existing['station'] - known['station']) < 0.5
                for existing in slope_changes
            )
            
            if not exists:
                slope_changes.append(known)
        
        # Return sorted by station for consistent ordering
        return sorted(slope_changes, key=lambda x: x['station'])
    
    def _calculate_height_at_station(self, station):
        """
        Calculate elevation at a specific station along the alignment.
        
        Uses grade interpolation to find the height at any point along the alignment,
        handling both constant gradient segments and parabolic vertical curves.
        
        Args:
            station (float): Distance along alignment in meters
            
        Returns:
            float: Elevation at the station in meters
            
        Algorithm:
            - Finds segment containing the station
            - For constant gradient: height = start_height + distance * grade
            - For parabolic curves: uses quadratic interpolation between start and end grades
            - Extrapolates beyond last segment using end grade
        """
        # Find the segment containing this station
        for segment in self.vertical_segments:
            start_dist = segment['start_distance']
            length = segment['length']
            end_dist = start_dist + length
            
            if start_dist <= station <= end_dist:
                distance_into_segment = station - start_dist
                start_height = segment['start_height']
                start_grade = segment['start_grade']
                end_grade = segment['end_grade']
                
                # Linear calculation for constant gradient
                if segment['curve_type'] == '.CONSTANTGRADIENT.':
                    height = start_height + (distance_into_segment * start_grade)
                else:
                    # Parabolic interpolation for curved segments
                    if length > 0:
                        t = distance_into_segment / length  # Normalized position (0 to 1)
                        grade_change = end_grade - start_grade
                        current_grade = start_grade + (grade_change * t)
                        # Average grade method for parabolic curve
                        height = start_height + (distance_into_segment * (start_grade + current_grade) / 2)
                    else:
                        height = start_height
                
                return height
        
        # Extrapolate from last segment if station is beyond alignment end
        if self.vertical_segments:
            last_segment = self.vertical_segments[-1]
            last_station = last_segment['start_distance'] + last_segment['length']
            last_height = last_segment['start_height'] + (last_segment['length'] * last_segment['end_grade'])
            extra_distance = station - last_station
            return last_height + (extra_distance * last_segment['end_grade'])
        
        return 0.0


class SlopeMarkerFactory:
    """
    Factory class for creating slope analysis markers.
    
    Creates markers indicating slope changes and slope directions along an alignment:
    - Orange circle markers at grade transition points
    - Directional arrows (green upward, red downward) showing slope direction
    
    These markers help visualize the vertical profile characteristics of the alignment.
    
    Attributes:
        model (ifcopenshell.file): The IFC file being modified
        owner_history (IfcOwnerHistory): IFC ownership and history information
        context_3d (IfcGeometricRepresentationContext): The 3D geometric context for shapes
            
    Example:
        >>> factory = SlopeMarkerFactory(model, owner_history, context_3d)
        >>> circle = factory.create_slope_change_marker(slope_change_dict)
        >>> arrow = factory.create_directional_arrow(station=100.0, grade=0.05, height=10.0, is_upward=True)
    """
    
    def __init__(self, model, owner_history, context_3d):
        """
        Initialize the slope marker factory.
        
        Args:
            model (ifcopenshell.file): The IFC file being modified
            owner_history (IfcOwnerHistory): IFC ownership and history information
            context_3d (IfcGeometricRepresentationContext): 3D geometric context for shape representation
        """
        self.model = model
        self.owner_history = owner_history
        self.context_3d = context_3d
        
    def create_slope_change_marker(self, slope_change, radius=0.4, thickness=0.06,
                                   color=(1.0, 0.5, 0.0), pset_name="Pset_SlopeChange"):
        """
        Create an orange circle marker at a slope change point.
        
        These markers highlight locations where the alignment grade changes, such as
        transitions from one constant slope to another or at vertical curve endpoints.
        
        Args:
            slope_change (dict): Slope change information containing:
                - station (float): Distance along alignment in meters
                - from_grade (float): Previous grade in decimal form
                - to_grade (float): New grade in decimal form
                - height (float): Elevation at change point in meters
                - type (str): 'curve' or 'transition'
            radius (float, optional): Marker radius in meters. Defaults to 0.4m.
            thickness (float, optional): Marker thickness in meters. Defaults to 0.06m.
            color (tuple, optional): RGB color values (0-1 range). Defaults to orange (1.0, 0.5, 0.0).
            pset_name (str, optional): Property set name. Defaults to "Pset_SlopeChange".
            
        Returns:
            MarkerElement: The created marker element with circle geometry and slope change properties
            
        Properties Added:
            - StationNumber: Location along alignment
            - FromGradePercent/ToGradePercent: Grades in percentage form
            - FromGradeDecimal/ToGradeDecimal: Grades in decimal form
            - GradeChange: Magnitude of change in percentage
            - HeightAboveDatum: Elevation
            - ChangeType: 'curve' or 'transition'
            - MarkerColor: "Orange"
        """
        geometry = CircleMarker(self.model, radius, thickness, color)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Calculate grade change for property
        grade_change = slope_change['to_grade'] - slope_change['from_grade']
        
        # Add comprehensive slope change properties
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
        Create a directional arrow showing slope direction and magnitude.
        
        Arrows point along the alignment direction (forward with increasing stations).
        Color indicates slope: green for upward (positive grade), red for downward (negative grade).
        The arrow orientation is controlled by the placement RefDirection set to alignment direction.
        
        Args:
            station (float): Distance along alignment in meters
            grade (float): Grade value in decimal form (e.g., 0.05 = 5% upward slope)
            height (float): Elevation at arrow location in meters
            is_upward (bool, optional): True for positive slope (green), False for negative (red). Defaults to True.
            length (float, optional): Arrow length in meters. Defaults to 0.6m.
            width (float, optional): Arrow width in meters. Defaults to 0.3m.
            thickness (float, optional): Arrow thickness in meters. Defaults to 0.05m.
            segment_type (str, optional): Type identifier. Defaults to "intermediate".
            pset_name (str, optional): Property set name. Defaults to "Pset_SlopeInformation".
            
        Returns:
            MarkerElement: The created marker element with arrow geometry and slope properties
            
        Properties Added:
            - StationNumber: Location along alignment
            - GradePercent: Grade in percentage form
            - GradeDecimal: Grade in decimal form
            - SlopeDirection: "Upward" or "Downward"
            - HeightAboveDatum: Elevation
            - SegmentType: Segment classification
            - MarkerColor: "Green" or "Red"
            
        Note:
            The arrow geometry is created pointing in the +X direction. The placement's
            RefDirection should be set to the alignment direction to orient it correctly.
        """
        # Create arrow geometry with appropriate color
        geometry = DirectionalArrow(self.model, length, width, thickness, is_upward)
        marker_element = MarkerElement(self.model, geometry, self.owner_history, self.context_3d)
        
        # Add comprehensive slope information properties
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
    """
    Utility class for calculating spatial placements and orientations.
    
    Provides static methods for:
    - Extracting alignment direction from referent placements
    - Calculating perpendicular directions for station markers
    - Creating marker placements (perpendicular for circles/triangles)
    - Creating arrow placements (aligned with centerline direction)
    - Extracting 3D positions from IFC placement entities
    
    These calculations are essential for correctly orienting markers relative to the
    alignment geometry, ensuring markers appear perpendicular or parallel as intended.
    
    All methods are static as they perform pure geometric calculations without state.
    """
    
    @staticmethod
    def calculate_alignment_direction(placement):
        """
        Extract the alignment direction vector from a referent placement.
        
        The alignment direction is the forward direction along the alignment centerline,
        pointing in the direction of increasing stations. This is extracted from the
        RefDirection of the referent's IfcAxis2Placement3D.
        
        Args:
            placement (IfcLinearPlacement): The placement entity with PlacementRelTo referencing alignment
            
        Returns:
            tuple: Normalized 3D direction vector (x, y, z) pointing along the alignment,
                   or (1.0, 0.0, 0.0) as default if extraction fails
                   
        Implementation:
            - Follows PlacementRelTo chain to find IfcAxis2Placement3D
            - Extracts RefDirection (alignment forward direction)
            - Normalizes to unit vector
            - Returns X-axis default if RefDirection is not defined
        """
        try:
            # Navigate to the relative placement from referent
            rel_placement = placement.RelativePlacement
            if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                align_dir = rel_placement.RefDirection.DirectionRatios
                # Normalize to unit vector
                length = math.sqrt(align_dir[0]**2 + align_dir[1]**2 + align_dir[2]**2)
                if length > 0.001:
                    return (align_dir[0]/length, align_dir[1]/length, align_dir[2]/length)
        except Exception:
            pass
        
        # Default alignment direction (X-axis)
        return (1.0, 0.0, 0.0)
    
    @staticmethod
    def calculate_perpendicular_direction(placement):
        """
        Calculate perpendicular direction to alignment for station markers.
        
        Computes a direction perpendicular to the alignment's forward direction in the
        horizontal (XY) plane. This is used for orienting markers (triangles and circles)
        so they stand perpendicular to the centerline.
        
        Args:
            placement (IfcLinearPlacement): The placement entity with PlacementRelTo referencing alignment
            
        Returns:
            tuple: Normalized 3D direction vector (x, y, z) perpendicular to alignment,
                   or (0.0, 1.0, 0.0) as default if extraction fails
                   
        Implementation:
            - Extracts alignment direction from RefDirection
            - Rotates 90° counterclockwise in XY plane: (dx, dy) -> (-dy, dx)
            - Normalizes result to unit vector
            - Z-component is always 0 (horizontal perpendicular)
        """
        try:
            rel_placement = placement.RelativePlacement
            if hasattr(rel_placement, 'RefDirection') and rel_placement.RefDirection:
                align_dir = rel_placement.RefDirection.DirectionRatios
                # Normalize alignment direction
                length = math.sqrt(align_dir[0]**2 + align_dir[1]**2 + align_dir[2]**2)
                align_normalized = (align_dir[0]/length, align_dir[1]/length, align_dir[2]/length)
                
                # Calculate perpendicular: rotate 90° counterclockwise in XY plane
                perp_dir = (-align_normalized[1], align_normalized[0], 0.0)
                perp_length = math.sqrt(perp_dir[0]**2 + perp_dir[1]**2)
                
                if perp_length > 0.001:
                    return (perp_dir[0]/perp_length, perp_dir[1]/perp_length, 0.0)
        except Exception:
            pass
        
        # Default perpendicular direction (Y-axis)
        return (0.0, 1.0, 0.0)
    
    @staticmethod
    def create_marker_placement(model, referent_placement, height_offset=0.5):
        """
        Create placement for station markers (triangles and circles) perpendicular to alignment.
        
        Constructs an IfcLocalPlacement with:
        - Location offset vertically above the alignment by height_offset
        - Y-axis (RefDirection) oriented perpendicular to the alignment
        - Z-axis pointing upward
        - Placement relative to the referent placement
        
        This orientation makes triangles and circles stand perpendicular to the alignment,
        like signs along a road.
        
        Args:
            model (ifcopenshell.file): The IFC file
            referent_placement (IfcLocalPlacement): Base placement at the station point
            height_offset (float, optional): Vertical offset above alignment in meters. Defaults to 0.5m.
            
        Returns:
            IfcLocalPlacement: Placement for the marker with perpendicular orientation
            
        Coordinate System:
            - Origin: (0, 0, height_offset) relative to referent
            - X-axis: Not explicitly set (derives from Y and Z)
            - Y-axis (RefDirection): Perpendicular to alignment in horizontal plane
            - Z-axis (Axis): Vertical (0, 0, 1)
        """
        perp_dir = PlacementCalculator.calculate_perpendicular_direction(referent_placement)
        
        # Position marker vertically above the alignment point
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
    def create_arrow_placement(model, referent_placement, height_offset=0.8):
        """
        Create placement for directional arrows pointing along alignment direction.
        
        Constructs an IfcLocalPlacement with:
        - Location offset vertically above the alignment by height_offset
        - X-axis (RefDirection) oriented along the alignment direction
        - Z-axis pointing upward
        - Placement relative to the referent placement
        
        This orientation makes arrows point forward along the centerline with increasing stations,
        showing the slope direction.
        
        Args:
            model (ifcopenshell.file): The IFC file
            referent_placement (IfcLocalPlacement): Base placement at the station point
            height_offset (float, optional): Vertical offset above alignment in meters. Defaults to 0.8m.
            
        Returns:
            IfcLocalPlacement: Placement for the arrow with alignment direction orientation
            
        Coordinate System:
            - Origin: (0, 0, height_offset) relative to referent
            - X-axis (RefDirection): Along alignment forward direction
            - Y-axis: Not explicitly set (derives from X and Z)
            - Z-axis (Axis): Vertical (0, 0, 1)
            
        Note:
            Arrow geometry is created pointing in +X direction, so setting RefDirection
            to the alignment direction makes the arrow point correctly along the centerline.
        """
        # Calculate the alignment direction vector
        align_dir = PlacementCalculator.calculate_alignment_direction(referent_placement)
        
        # Position arrow vertically above the alignment point
        offset_point = model.create_entity(
            "IfcCartesianPoint", 
            Coordinates=(0.0, 0.0, height_offset)
        )
        
        # Orientation: X-axis along alignment direction, Z-axis up
        # This makes the arrow point along the alignment with increasing stations
        x_direction = model.create_entity("IfcDirection", DirectionRatios=align_dir)
        z_direction = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
        
        local_axis_placement = model.create_entity(
            "IfcAxis2Placement3D",
            Location=offset_point,
            Axis=z_direction,
            RefDirection=x_direction
        )
        
        return model.create_entity(
            "IfcLocalPlacement",
            PlacementRelTo=referent_placement,
            RelativePlacement=local_axis_placement
        )
    
    @staticmethod
    def extract_position(placement):
        """
        Extract 3D position coordinates from an IFC placement entity.
        
        Utility method to retrieve the (x, y, z) coordinates from a placement's
        Location point. Handles extraction errors gracefully.
        
        Args:
            placement (IfcLinearPlacement or IfcLocalPlacement): Placement entity
            
        Returns:
            tuple: 3D coordinates (x, y, z) in meters, or (0.0, 0.0, 0.0) if extraction fails
        """
        try:
            rel_placement = placement.RelativePlacement
            location = rel_placement.Location.Coordinates
            return location
        except Exception:
            return (0.0, 0.0, 0.0)


class TextLiteralCreator:
    """
    Creates IFC text literals with styling for station labels.
    
    Provides methods to create text annotations that display station information.
    Handles both IfcTextLiteral (standard IFC text) and polyline fallback
    (for viewers that don't support text literals).
    
    Attributes:
        model (ifcopenshell.file): The IFC file being modified
        context_3d (IfcGeometricRepresentationContext): 3D geometric context for text placement
        
    Example:
        >>> creator = TextLiteralCreator(model, context_3d)
        >>> text_rep = creator.create_text_literal_representation("Station 100", height=1.0)
    """
    
    def __init__(self, model, context_3d):
        """
        Initialize text literal creator.
        
        Args:
            model (ifcopenshell.file): The IFC file being modified
            context_3d (IfcGeometricRepresentationContext): 3D geometric context for shape representation
        """
        self.model = model
        self.context_3d = context_3d
        
    def create_text_literal_representation(self, text, position_offset=(0.0, 0.2, 0.0),
                                          height=1.0, color=(0.0, 0.0, 0.0), weight="normal"):
        """
        Create an IfcTextLiteral shape representation with styling.
        
        Creates styled 3D text that can be viewed in IFC viewers supporting text literals.
        Includes font styling (height, weight) and color.
        
        Args:
            text (str): Text content to display
            position_offset (tuple, optional): XYZ offset for text position relative to marker.
                                              Defaults to (0.0, 0.2, 0.0) - offset in Y direction.
            height (float, optional): Text height in meters. Defaults to 1.0m.
            color (tuple, optional): RGB color values (0-1 range). Defaults to black (0.0, 0.0, 0.0).
            weight (str, optional): Font weight, "normal" or "bold". Defaults to "normal".
            
        Returns:
            IfcShapeRepresentation: Text representation with type "Annotation" and identifier "Annotation"
            
        Implementation:
            - Creates IfcAxis2Placement3D for text orientation (X-axis right, Y-axis forward)
            - Creates IfcTextLiteralWithExtent with box for text bounds
            - Applies IfcTextStyleFontModel for font properties
            - Applies IfcSurfaceStyleRendering for color
            - Returns styled shape representation
        """
        # Create text placement: X-axis to the right, Y-axis forward
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
        Create polyline-based text representation as fallback for non-supporting viewers.
        
        Creates text using polyline curves instead of IfcTextLiteral. This provides better
        compatibility with IFC viewers that don't support text literals, as all viewers
        can display geometric curves.
        
        Args:
            text (str): Text content to display
            height (float, optional): Text height in meters. Defaults to 1.0m.
            width_factor (float, optional): Width-to-height ratio for character spacing. Defaults to 0.6.
            
        Returns:
            IfcShapeRepresentation or None: Polyline representation with type "GeometricCurveSet",
                                            or None if polyline generation fails
                                            
        Implementation:
            - Uses TextAnnotation class from geometry_markers to generate polylines
            - Each character is represented as a set of line segments
            - Returns GeometricCurveSet representation for maximum compatibility
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
    """
    Main orchestrator for creating alignment markers and optional slope analysis.
    
    This class coordinates the entire workflow of:
    1. Finding alignments in the IFC model
    2. Extracting alignment geometry (horizontal, vertical, referent points)
    3. Creating station markers (triangles and circles) with text annotations
    4. Optionally detecting slope changes and creating slope markers
    5. Assigning all markers to spatial structure
    
    The processor uses factory classes for marker creation and utility classes for
    calculations, providing a clean separation of concerns.
    
    Attributes:
        model (ifcopenshell.file): The IFC file being processed
        config (dict): Configuration dictionary with all user settings
        project (IfcProject): The IFC project entity
        owner_history (IfcOwnerHistory): IFC ownership information
        context_3d (IfcGeometricRepresentationContext): 3D context for geometry
        station_factory (StationMarkerFactory): Factory for creating station markers
        text_creator (TextLiteralCreator): Creator for text annotations
        
    Example:
        >>> processor = AlignmentMarkerProcessor(model, config)
        >>> processor.process_alignment(alignment, add_slope_analysis=True)
    """
    
    def __init__(self, model, config):
        """
        Initialize the alignment marker processor.
        
        Sets up the processor with necessary IFC entities and creates factory instances
        for marker and text creation.
        
        Args:
            model (ifcopenshell.file): The IFC model to process
            config (dict): Configuration dictionary containing all user-defined parameters
                          (marker sizes, offsets, text heights, colors, etc.)
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
        # Find the first 3D geometric context for shape representations
        for context in contexts:
            if hasattr(context, 'ContextType') and context.ContextType == '3D':
                return context
        # Fallback to first context if no 3D context found
        return contexts[0] if contexts else None
    
    def process_station_markers(self):
        """
        Process all referent points and create station markers with text annotations.
        
        This method:
        1. Finds all IfcReferent entities (station points along the alignment)
        2. Determines start and end stations for special circle marker placement
        3. Creates triangle markers for intermediate stations
        4. Creates circle markers for start and end stations
        5. Adds text annotations showing station number, offset, and elevation
        6. Adds both IfcTextLiteral and polyline fallback representations
        
        Returns:
            list: All created IFC elements (IfcBuildingElementProxy and IfcAnnotation)
            
        Station Marker Rules:
            - Start station (minimum): Red circle marker
            - End station (maximum): Red circle marker
            - Intermediate stations: Green triangle markers
            - All stations: Get text annotations with station info
            
        Text Content Format:
            "Station XXX\\nOffset: YYY m\\nElevation: ZZZ m"
        """
        referents = self.model.by_type("IfcReferent")
        print(f"Found {len(referents)} IFCREFERENT objects")
        
        # Determine start and end stations by finding min/max station values
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
        
        # Process each referent point to create markers
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
        Create orange circle markers and text annotations for slope change points.
        
        Processes detected slope changes to create visual markers indicating where
        the alignment grade changes significantly. Each change gets:
        - Orange circle marker positioned perpendicular to alignment
        - Text annotation showing grade transition details
        
        Args:
            slope_changes (list): List of slope change dictionaries from SlopeChangeDetector
            referent_map (dict): Mapping from station values to IfcReferent entities
            
        Returns:
            list: Created IFC elements (IfcBuildingElementProxy and IfcAnnotation)
            
        Implementation:
            - Finds nearest referent for placement (uses exact match or closest station)
            - Creates markers at configured height offset above alignment
            - Annotates with from/to grade information
            - Handles missing referents gracefully by skipping
        """
        elements = []
        
        for change in slope_changes:
            station = change['station']
            
            # Find referent for this station (exact or nearest)
            base_referent = referent_map.get(station)
            if not base_referent:
                nearest_station = min(referent_map.keys(), 
                                    key=lambda s: abs(s - station))
                base_referent = referent_map[nearest_station]
            
            if not base_referent or not base_referent.ObjectPlacement:
                continue
            
            # Create placement for slope change marker (perpendicular orientation)
            offset_height = self.config['slope_marker_height_offset']
            
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
            
            # Create arrow placement - oriented along alignment direction
            offset_height = self.config['arrow_height_offset']
            
            arrow_placement = PlacementCalculator.create_arrow_placement(
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
    Main entry point for creating alignment markers with optional slope analysis.
    
    This function orchestrates the complete workflow:
    1. Opens the input IFC file
    2. Creates station markers (triangles/circles) at all referent points
    3. Optionally performs slope analysis and creates slope markers
    4. Assigns all elements to the spatial structure
    5. Saves the modified model to the output file
    
    Args:
        input_file (str): Path to input IFC file containing alignment with referents
        output_file (str): Path where modified IFC file will be saved
        add_slope_analysis (bool, optional): Enable slope change detection and markers.
                                             Defaults to True.
        **config: Configuration parameters passed as keyword arguments:
            - triangle_height (float): Triangle marker height in meters
            - triangle_thickness (float): Triangle marker thickness in meters
            - triangle_color (tuple): RGB color for triangles (0-1 range)
            - circle_radius (float): Circle marker radius in meters
            - circle_thickness (float): Circle marker thickness in meters
            - circle_color (tuple): RGB color for circles (0-1 range)
            - text_height (float): Text annotation height in meters
            - text_color (tuple): RGB color for text (0-1 range)
            - text_position_offset (tuple): XYZ offset for text position
            - marker_height_offset (float): Vertical offset for markers
            - slope_marker_height_offset (float): Vertical offset for slope markers
            - arrow_height_offset (float): Vertical offset for arrows
            - grade_change_threshold (float): Minimum grade change to detect (decimal)
            - known_slope_changes (list): Optional list of manually specified slope changes
            
    Returns:
        None: Saves output to file specified by output_file parameter
        
    Prints:
        - Progress information about markers created
        - Statistics on station markers, slope changes, and directional arrows
        - Spatial assignment confirmation
        - Output file path
        
    Example:
        >>> create_alignment_markers(
        ...     "input.ifc",
        ...     "output.ifc",
        ...     add_slope_analysis=True,
        ...     triangle_height=0.5,
        ...     circle_radius=0.4
        ... )
    """
    # Load the IFC model
    model = ifcopenshell.open(input_file)
    
    # Initialize the alignment marker processor with configuration
    processor = AlignmentMarkerProcessor(model, config)
    
    # STEP 1: Create station markers at all referent points
    print("\n" + "="*60)
    print("CREATING STATION MARKERS")
    print("="*60)
    station_elements = processor.process_station_markers()
    
    all_elements = station_elements
    slope_elements = []
    
    # STEP 2: Optionally add slope analysis
    if add_slope_analysis:
        print("\n" + "="*60)
        print("ADDING SLOPE ANALYSIS")
        print("="*60)
        
        # Extract vertical alignment segments
        vertical_segments = processor.extract_vertical_segments()
        print(f"Found {len(vertical_segments)} vertical segments")
        
        if vertical_segments:
            # Build mapping from station values to referent entities
            referent_map = processor.build_referent_map()
            print(f"Found {len(referent_map)} station referents")
            
            # Detect significant grade changes
            detector = SlopeChangeDetector(vertical_segments, config.get('grade_change_threshold', 0.01))
            slope_changes = detector.detect_slope_changes()
            
            # Optionally add manually specified slope changes
            if 'known_slope_changes' in config:
                slope_changes = detector.add_known_changes(slope_changes, config['known_slope_changes'])
            
            print(f"Identified {len(slope_changes)} slope change points")
            
            # Create slope change markers (orange circles at grade transitions)
            slope_change_elements = processor.process_slope_changes(slope_changes, referent_map)
            
            # Create directional arrows at stations showing slope direction
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
    """
    Configuration Section
    
    This section contains all user-configurable parameters for the alignment marker
    creation process. Adjust these values to customize marker appearance, positioning,
    and behavior.
    
    Parameter Groups:
    -----------------
    1. Input/Output Files: Specify source and destination IFC files
    2. Feature Flags: Enable/disable slope analysis
    3. Station Markers: Configure triangles and circles for stations
    4. Text Settings: Control text appearance and positioning
    5. Slope Analysis: Configure slope change detection and markers
    
    Units:
    ------
    - All dimensions are in meters
    - All colors are RGB tuples with values from 0.0 to 1.0
    - Grades/slopes are in decimal form (e.g., 0.05 = 5% grade)
    """
    
    # ============================================================================
    # INPUT/OUTPUT FILES
    # ============================================================================
    
    INPUT_FILE = "m_f-veg_CL-1000.ifc"  # Path to input IFC file with alignment
    OUTPUT_FILE = "m_f-veg_CL-1000_with_markers.ifc"  # Path for output IFC file
    
    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    
    # Set to True to include slope analysis (orange circles and directional arrows)
    # Set to False to only create station markers (triangles and circles)
    ADD_SLOPE_ANALYSIS = True
    
    # ============================================================================
    # STATION MARKER SETTINGS
    # ============================================================================
    
    # Triangle Markers (Intermediate Stations)
    # -----------------------------------------
    # Green triangular markers placed at regular stations along the alignment
    TRIANGLE_HEIGHT = 0.5           # Height of triangle in meters
    TRIANGLE_THICKNESS = 0.01       # Thickness of triangle disk in meters
    TRIANGLE_COLOR = (0.0, 0.8, 0.0)  # RGB color: Green (R=0.0, G=0.8, B=0.0)
    
    # Circle Markers (Start/End Stations)
    # -----------------------------------
    # Red circular markers placed at alignment start and end points
    CIRCLE_RADIUS = 0.5             # Radius of circle in meters
    CIRCLE_THICKNESS = 0.01         # Thickness of circle disk in meters
    CIRCLE_COLOR = (1.0, 0.0, 0.0)  # RGB color: Red (R=1.0, G=0.0, B=0.0)
    
    # Text Annotation Settings
    # ------------------------
    # Text labels showing station number, offset, and elevation
    TEXT_HEIGHT = 1.0               # Height of text characters in meters
    TEXT_WIDTH_FACTOR = 0.6         # Width-to-height ratio for characters (0.6 = 60% of height)
    TEXT_COLOR = (0.0, 0.0, 0.0)    # RGB color: Black (R=0.0, G=0.0, B=0.0)
    
    # Marker Positioning
    # ------------------
    # Vertical offsets control how far above the alignment centerline markers appear
    MARKER_HEIGHT_OFFSET = 0.5      # Vertical offset for station markers (meters)
    TEXT_POSITION_OFFSET = (0.0, 0.2, 0.0)  # XYZ offset: (right, forward, up) from marker
    
    # ============================================================================
    # SLOPE ANALYSIS SETTINGS (only active if ADD_SLOPE_ANALYSIS = True)
    # ============================================================================
    
    # Slope Change Markers (Orange Circles)
    # --------------------------------------
    # Orange circular markers placed at points where alignment grade changes significantly
    SLOPE_MARKER_RADIUS = 0.4           # Radius of slope change circle in meters
    SLOPE_MARKER_THICKNESS = 0.05       # Thickness of circle disk in meters
    SLOPE_MARKER_COLOR = (1.0, 0.5, 0.0)  # RGB color: Orange (R=1.0, G=0.5, B=0.0)
    SLOPE_MARKER_HEIGHT_OFFSET = 1.0    # Vertical offset above centerline in meters
    
    # Directional Arrows (Green/Red Slope Indicators)
    # ------------------------------------------------
    # Arrows pointing along alignment showing slope direction:
    # - Green arrows for upward slopes (positive grade)
    # - Red arrows for downward slopes (negative grade)
    ARROW_LENGTH = 0.5                  # Length of arrow body in meters
    ARROW_WIDTH = 0.25                  # Width of arrow in meters
    ARROW_THICKNESS = 0.05              # Thickness of arrow in meters
    ARROW_HEIGHT_OFFSET = 0.8           # Vertical offset above centerline in meters
    
    # Slope Text Annotation Settings
    # -------------------------------
    # Text annotations for slope information at various detail levels
    TEXT_HEIGHT_LARGE = 0.6             # Large text for major information (meters)
    TEXT_HEIGHT_MEDIUM = 0.5            # Medium text for standard labels (meters)
    TEXT_HEIGHT_SMALL = 0.4             # Small text for detailed info (meters)
    TEXT_COLOR_SLOPE = (0.0, 0.0, 0.8)  # RGB color: Dark Blue (R=0.0, G=0.0, B=0.8)
    TEXT_FONT = "Arial"                 # Font family name
    
    # Property Set Configuration
    # --------------------------
    PROPERTY_SET_NAME = "Pset_SlopeInformation"  # IFC property set name for slope data
    
    # Slope Detection Threshold
    # -------------------------
    # Minimum grade change to trigger slope change marker creation
    # Value is in decimal form: 0.01 = 1% grade change
    # Smaller values = more sensitive detection, more markers created
    GRADE_CHANGE_THRESHOLD = 0.01
    
    # Manual Slope Changes (Optional)
    # -------------------------------
    # List of dictionaries specifying known slope changes to add regardless of detection
    # Useful for important design points that may fall below the threshold
    # Format: [{'station': 123.45, 'from_grade': 0.02, 'to_grade': -0.03, 'height': 10.5, 'type': 'manual'}]
    KNOWN_SLOPE_CHANGES = []  # Leave empty if not needed
    
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
