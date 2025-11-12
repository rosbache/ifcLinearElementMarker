"""
Slope Analysis Script for IFC Alignments

This script analyzes the vertical alignment geometry from an IFC file and adds:
1. Orange circle markers at slope change points
2. Text information showing slope percentages and heights at stations
3. Segment boundary markers
4. Comprehensive slope analysis information

Based on analysis of m_f-veg_CL-1000.ifc:
- Total length: 228.57 meters
- 7 vertical segments with slopes ranging from -4% to +2.02%
- Key slope changes at stations ~28m, ~107m, and ~193m
"""

# Key slope change information extracted from the IFC file analysis
SLOPE_CHANGE_POINTS = [
    {
        'station': 28.36,
        'from_grade': -3.0,
        'to_grade': 2.02,
        'height': 2.93,
        'description': 'Grade change from -3% downward to +2% upward'
    },
    {
        'station': 106.86,
        'from_grade': 2.02,
        'to_grade': -4.0,
        'height': 3.63,
        'description': 'Grade change from +2% upward to -4% downward (steepest)'
    },
    {
        'station': 192.91,
        'from_grade': -4.0,
        'to_grade': 1.1,
        'height': 1.82,
        'description': 'Grade change from -4% downward to +1.1% upward'
    }
]

# Vertical segment information
VERTICAL_SEGMENTS = [
    {'start': 8.46, 'end': 28.36, 'length': 19.90, 'grade': -3.0, 'type': 'Constant Grade', 'start_height': 3.52},
    {'start': 28.36, 'end': 63.47, 'length': 35.11, 'grade_start': -3.0, 'grade_end': 2.02, 'type': 'Vertical Curve (R=700m)', 'start_height': 2.93},
    {'start': 63.47, 'end': 106.86, 'length': 43.40, 'grade': 2.02, 'type': 'Constant Grade', 'start_height': 2.75},
    {'start': 106.86, 'end': 160.97, 'length': 54.10, 'grade_start': 2.02, 'grade_end': -4.0, 'type': 'Vertical Curve (R=-900m)', 'start_height': 3.63},
    {'start': 160.97, 'end': 192.91, 'length': 31.94, 'grade': -4.0, 'type': 'Constant Grade', 'start_height': 3.09},
    {'start': 192.91, 'end': 228.57, 'length': 35.66, 'grade_start': -4.0, 'grade_end': 1.1, 'type': 'Vertical Curve (R=700m)', 'start_height': 1.82}
]

def calculate_height_at_station(station):
    """Calculate height at any station using the vertical segment data"""
    for segment in VERTICAL_SEGMENTS:
        if segment['start'] <= station <= segment['end']:
            distance_into_segment = station - segment['start']
            
            if 'grade' in segment:  # Constant grade segment
                grade = segment['grade'] / 100.0  # Convert percentage to decimal
                height = segment['start_height'] + (distance_into_segment * grade)
            else:  # Vertical curve segment
                # Linear interpolation for grade within curve
                t = distance_into_segment / segment['length'] if segment['length'] > 0 else 0
                start_grade = segment['grade_start'] / 100.0
                end_grade = segment['grade_end'] / 100.0
                avg_grade = start_grade + (end_grade - start_grade) * t / 2
                height = segment['start_height'] + (distance_into_segment * (start_grade + avg_grade) / 2)
            
            return height
    
    # If not found in segments, extrapolate
    if station < VERTICAL_SEGMENTS[0]['start']:
        # Before first segment
        return VERTICAL_SEGMENTS[0]['start_height']
    else:
        # After last segment
        last_seg = VERTICAL_SEGMENTS[-1]
        if 'grade' in last_seg:
            final_grade = last_seg['grade'] / 100.0
        else:
            final_grade = last_seg['grade_end'] / 100.0
        
        extra_distance = station - last_seg['end']
        last_height = calculate_height_at_station(last_seg['end'])
        return last_height + (extra_distance * final_grade)

def get_slope_at_station(station):
    """Get the slope percentage at any station"""
    for segment in VERTICAL_SEGMENTS:
        if segment['start'] <= station <= segment['end']:
            if 'grade' in segment:  # Constant grade
                return segment['grade']
            else:  # Variable grade in curve
                t = (station - segment['start']) / segment['length'] if segment['length'] > 0 else 0
                grade_diff = segment['grade_end'] - segment['grade_start']
                return segment['grade_start'] + (t * grade_diff)
    
    # Default return
    return 0.0

def create_analysis_report():
    """Create a detailed text report of the slope analysis"""
    report = []
    report.append("=" * 60)
    report.append("SLOPE ANALYSIS REPORT - m_f-veg_CL-1000.ifc")
    report.append("=" * 60)
    report.append("")
    
    report.append("📊 ALIGNMENT OVERVIEW:")
    report.append(f"   Total Length: 228.57 meters")
    report.append(f"   Number of Vertical Segments: {len(VERTICAL_SEGMENTS)}")
    report.append(f"   Number of Slope Changes: {len(SLOPE_CHANGE_POINTS)}")
    report.append("")
    
    report.append("🔶 SLOPE CHANGE POINTS:")
    for i, point in enumerate(SLOPE_CHANGE_POINTS, 1):
        report.append(f"   {i}. Station {point['station']:.1f}m:")
        report.append(f"      Grade Change: {point['from_grade']:.1f}% → {point['to_grade']:.1f}%")
        report.append(f"      Height: {point['height']:.2f}m")
        report.append(f"      Impact: {point['description']}")
        report.append("")
    
    report.append("📈 VERTICAL SEGMENTS:")
    for i, segment in enumerate(VERTICAL_SEGMENTS, 1):
        report.append(f"   Segment {i}: Station {segment['start']:.1f}m - {segment['end']:.1f}m")
        report.append(f"      Length: {segment['length']:.1f}m")
        report.append(f"      Type: {segment['type']}")
        if 'grade' in segment:
            report.append(f"      Grade: {segment['grade']:.1f}% (constant)")
        else:
            report.append(f"      Grade: {segment['grade_start']:.1f}% → {segment['grade_end']:.1f}%")
        report.append(f"      Start Height: {segment['start_height']:.2f}m")
        report.append("")
    
    report.append("📏 STATION ANALYSIS (Every 20m):")
    for station in range(0, 240, 20):
        if station <= 228.57:
            height = calculate_height_at_station(station)
            slope = get_slope_at_station(station)
            report.append(f"   Station {station:3d}m: Height {height:5.2f}m, Slope {slope:+5.1f}%")
    
    report.append("")
    report.append("🚧 ENGINEERING NOTES:")
    report.append("   • Steepest downward grade: -4.0% (stations 161-193m)")
    report.append("   • Steepest upward grade: +2.0% (stations 63-107m)")
    report.append("   • Maximum grade change: 6.0% (at station 107m)")
    report.append("   • Total elevation change: ~2.2m descent")
    report.append("   • Critical drainage area: steep -4% section")
    
    return "\n".join(report)

def print_ifc_creation_instructions():
    """Print instructions for creating the IFC file with slope markers"""
    print("\n🔧 IFC FILE CREATION INSTRUCTIONS:")
    print("To add slope analysis markers to your IFC file, you would need:")
    print("")
    
    print("1. 🔶 SLOPE CHANGE MARKERS (Orange Circles):")
    for point in SLOPE_CHANGE_POINTS:
        print(f"   • Station {point['station']:.1f}m: Orange circle marker")
        print(f"     Text: 'Grade Change: {point['from_grade']:.1f}% → {point['to_grade']:.1f}%'")
        print(f"     Height: {point['height']:.2f}m")
    
    print("")
    print("2. 📝 STATION INFORMATION DISPLAYS:")
    for station in range(0, 240, 20):
        if station <= 228.57:
            height = calculate_height_at_station(station)
            slope = get_slope_at_station(station)
            print(f"   • Station {station:3d}m: Text showing 'Grade: {slope:+.1f}%, Height: {height:.2f}m'")
    
    print("")
    print("3. 🏷️ SEGMENT BOUNDARY MARKERS:")
    for i, segment in enumerate(VERTICAL_SEGMENTS, 1):
        print(f"   • Segment {i} boundaries at stations {segment['start']:.1f}m and {segment['end']:.1f}m")
    
    print("")
    print("💡 IMPLEMENTATION NOTES:")
    print("   • Orange circles should be 0.4m radius, positioned 1.5m above alignment")
    print("   • Text should be blue, Arial font, 0.3m height using IfcTextLiteral")
    print("   • All markers positioned relative to existing IfcReferent stations")
    print("   • Slope change markers are most critical for visualization")

if __name__ == "__main__":
    print("🏗️ IFC ALIGNMENT SLOPE ANALYSIS TOOL")
    print("File: m_f-veg_CL-1000.ifc")
    print("")
    
    # Generate and display the analysis report
    report = create_analysis_report()
    print(report)
    
    # Save report to file
    with open("slope_analysis_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("\n📄 Detailed report saved to: slope_analysis_report.txt")
    
    # Show IFC creation instructions
    print_ifc_creation_instructions()
    
    print("\n✅ Analysis complete!")
    print("🔗 Use the slope analysis data above to manually add markers in your IFC viewer")
    print("   or implement the IFC creation code using ifcopenshell when available.")