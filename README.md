# IFC Alignment Marker System

Automatically generate visual station markers, text labels, and slope analysis along alignment centerlines in IFC files using an object-oriented Python architecture.

This image shows the result in Trimble Connect Online Viewer. The result in other viewers may be different due to different support of IfcAnnotation and IfcTextLiteral.

<img width="855" height="769" alt="image" src="https://github.com/user-attachments/assets/c524af4f-6d07-42a3-85f8-ba4c870ba6e9" />

This is the same file in Blender/Bonsai (0.8.3 post1)
<img width="592" height="499" alt="image" src="https://github.com/user-attachments/assets/bd78ddb6-304d-47b6-acde-4acd8ed02f22" />

This is the same file in BIMvision display IfcTextLiteral alongside the IfcAnnotation (only visible after double clicking on the annotation object in the ifc file tree.

<img width="578" height="480" alt="image" src="https://github.com/user-attachments/assets/219b4f75-b051-441b-b146-cb18c60cfe46" />

## Overview

This project provides an object-oriented Python system that reads IFC files containing alignment data with `IfcReferent` objects and creates:
- **Station markers** with text labels at each station point
- **Slope analysis** with grade change markers and directional arrows (optional)

The system uses a modular, extensible architecture with shared geometry classes and specialized processors.

## Features

### Station Markers

- **Dual Marker Types**:
  - 🔺 **Green triangles** for intermediate stations
  - 🔴 **Red circles** for start/end stations
  
- **Dual Text Representation** (maximum compatibility):
  - `IfcTextLiteral` with `IfcTextStyle` - Modern styled text for advanced viewers
  - `IfcAnnotation` with polyline geometry - Fallback for basic viewers
  
- **Smart Positioning**:
  - Markers positioned above the alignment line
  - Automatic perpendicular orientation to alignment direction
  - Configurable height offsets and dimensions

### Slope Analysis (Optional)

- **Slope Change Detection**:
  - 🟠 **Orange circles** at grade change points
  - Automatic detection of transitions between constant grades and curves
  - Support for known slope change points
  
- **Directional Arrows**:
  - 🟢 **Green arrows** for positive (upward) slopes
  - 🔴 **Red arrows** for negative (downward) slopes
  - Arrows point along alignment direction with increasing stations
  
- **Comprehensive Information**:
  - Grade percentages and decimal values
  - Height above datum at each point
  - Slope direction indicators
  - Change type classification

### Architecture

- **Object-Oriented Design**: Modular classes with clear responsibilities
- **Shared Geometry Module**: Reusable marker geometry classes
- **Factory Pattern**: Centralized marker creation logic
- **Configurable**: All parameters adjustable via configuration dictionaries
- **Extensible**: Easy to add new marker types or analysis features

## Requirements

```bash
pip install ifcopenshell
```

Python 3.6 or higher recommended.

## Quick Start

### Basic Usage (Station Markers Only)

```python
python create_alignment_markers_oop.py
```

This will:
1. Read from `m_f-veg_CL-1000.ifc` (input file)
2. Create station markers (triangles and circles) with text labels
3. Save to `m_f-veg_CL-1000_with_markers.ifc` (output file)

### With Slope Analysis (Default)

The script includes slope analysis by default. To disable it, edit the configuration:

```python
# In create_alignment_markers_oop.py
ADD_SLOPE_ANALYSIS = False  # Set to False to only create station markers
```

### Customizing Files

Edit the configuration section in `create_alignment_markers_oop.py`:

```python
INPUT_FILE = "your_input_file.ifc"
OUTPUT_FILE = "your_output_file.ifc"
ADD_SLOPE_ANALYSIS = True  # Enable/disable slope analysis
```

## Configuration

All parameters are easily configurable in the `USER CONFIGURABLE PARAMETERS` section at the bottom of `create_alignment_markers_oop.py`.

### Station Marker Settings

```python
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
```

### Slope Analysis Settings (when enabled)

```python
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
TEXT_HEIGHT_LARGE = 0.6             # Height for large text in meters
TEXT_HEIGHT_MEDIUM = 0.5            # Height for medium text in meters
TEXT_HEIGHT_SMALL = 0.4             # Height for small text in meters
TEXT_COLOR_SLOPE = (0.0, 0.0, 0.8)  # RGB color for slope text (DarkBlue)
TEXT_FONT = "Arial"                 # Font family

# Detection Settings
GRADE_CHANGE_THRESHOLD = 0.01  # Minimum grade change to detect (1%)

# Known Slope Changes (optional)
KNOWN_SLOPE_CHANGES = [
    {'station': 28.36, 'from_grade': -0.03, 'to_grade': 0.0202, 'height': 2.93, 'type': 'known'},
    # Add more known points as needed...
]
```

### Example Customizations

**Make Markers Larger and More Visible:**
```python
TRIANGLE_HEIGHT = 1.0
TRIANGLE_THICKNESS = 0.02
CIRCLE_RADIUS = 1.0
CIRCLE_THICKNESS = 0.02
TEXT_HEIGHT = 1.5
```

**Change Color Scheme:**
```python
TRIANGLE_COLOR = (0.0, 0.0, 1.0)  # Blue triangles
CIRCLE_COLOR = (1.0, 1.0, 0.0)    # Yellow circles
SLOPE_MARKER_COLOR = (1.0, 0.0, 1.0)  # Magenta slope markers
```

**Position Markers Higher Above Alignment:**
```python
MARKER_HEIGHT_OFFSET = 1.5      # 1.5m instead of 0.5m
ARROW_HEIGHT_OFFSET = 2.0       # 2.0m for arrows
```

## Output

### Station Markers

The script generates **2 IFC elements per station**:

1. **IfcBuildingElementProxy** - Contains:
   - Triangle or circle geometry (colored)
   - IfcTextLiteral with styling (modern text)
   - Property set with station metadata

2. **IfcAnnotation** - Contains:
   - Polyline-based text geometry (fallback)
   - Same positioning as marker

### Slope Analysis Elements (when enabled)

1. **Slope Change Markers** - Orange circles at grade change points
   - IfcBuildingElementProxy with circular geometry
   - Property set with grade change information
   - Positioned at detected or known slope change locations

2. **Directional Arrows** - Green/red arrows showing slope direction
   - IfcBuildingElementProxy with arrow geometry
   - Oriented along alignment direction
   - Color indicates slope direction (green=upward, red=downward)
   - Created at every other station

### Example Output

For a file with 24 stations and slope analysis enabled:
- **48 station marker elements** (24 markers + 24 text annotations)
  - 2 red circles at start/end stations
  - 22 green triangles at intermediate stations
- **18 slope analysis elements**
  - 6 orange slope change markers
  - 12 directional arrows (every other station)

## Marker Specifications

### Triangle Markers (Intermediate Stations)
- **Height**: Configurable (default: 0.5 meters)
- **Thickness**: Configurable (default: 0.01 meters)
- **Color**: Green RGB(0.0, 0.8, 0.0) - configurable
- **Orientation**: Perpendicular to alignment direction
- **Position**: Above alignment at configurable offset

### Circle Markers (Start/End Stations)
- **Radius**: Configurable (default: 0.5 meters)
- **Thickness**: Configurable (default: 0.01 meters)
- **Color**: Red RGB(1.0, 0.0, 0.0) - configurable
- **Orientation**: Vertical plane
- **Position**: Above alignment at configurable offset

### Slope Change Markers (Orange Circles)
- **Radius**: Configurable (default: 0.4 meters)
- **Thickness**: Configurable (default: 0.05 meters)
- **Color**: Orange RGB(1.0, 0.5, 0.0) - configurable
- **Orientation**: Perpendicular to alignment direction
- **Position**: Above alignment at configurable offset

### Directional Arrows (Slope Direction)
- **Length**: Configurable (default: 0.5 meters)
- **Width**: Configurable (default: 0.25 meters)
- **Thickness**: Configurable (default: 0.05 meters)
- **Color**: Green (upward slopes) or Red (downward slopes)
- **Orientation**: Along alignment direction (points forward with increasing stations)
- **Position**: Above alignment at configurable offset

### Text Labels
- **Height**: Configurable (default: 1.0 meters for station text)
- **Font**: Arial (for IfcTextLiteral)
- **Color**: Configurable (default: Black for stations, DarkBlue for slope info)
- **Content**: Station value (e.g., "0", "10", "100", "228.6")
- **Format**: Integer display for whole numbers, one decimal for fractional values

## Architecture

The system uses an object-oriented architecture with three main components:

### 1. Core Geometry Module (`geometry_markers.py`)

Shared geometry classes used by all marker types:

- **`BaseMarker`** - Abstract base class for all marker geometries
- **`TriangleMarker`** - Green triangular markers for intermediate stations
- **`CircleMarker`** - Circular markers (red for start/end, orange for slope changes)
- **`DirectionalArrow`** - Arrow geometry for slope direction indicators
- **`MarkerElement`** - Wraps geometry with properties and IFC element creation
- **`TextAnnotation`** - Creates polyline-based text rendering

### 2. Main Application (`create_alignment_markers_oop.py`)

Unified script for creating both station markers and slope analysis:

- **`StationMarkerFactory`** - Creates station marker instances
- **`SlopeMarkerFactory`** - Creates slope-related markers
- **`SlopeChangeDetector`** - Analyzes vertical alignment and detects grade changes
- **`PlacementCalculator`** - Calculates spatial placements and orientations
- **`TextLiteralCreator`** - Creates IFC text representations
- **`AlignmentMarkerProcessor`** - Main orchestration class

### Key Design Patterns

- **Factory Pattern**: Centralized marker creation
- **Strategy Pattern**: Different placement strategies for different marker types
- **Separation of Concerns**: Geometry separate from business logic
- **Shared Utilities**: Reusable placement and text creation classes

## IFC Structure

### Station Marker Entities

**For Each Station:**

1. **Marker (IfcBuildingElementProxy)**:
   - `IfcExtrudedAreaSolid` (triangle or circle geometry)
   - `IfcColourRgb` + `IfcSurfaceStyle` (color)
   - `IfcTextLiteral` + `IfcTextStyle` (styled text)
   - `IfcLocalPlacement` (positioning)
   - `IfcPropertySet` (station metadata)

2. **Text Annotation (IfcAnnotation)**:
   - `IfcPolyline` (text as line geometry)
   - `IfcShapeRepresentation` (annotation type)
   - `IfcLocalPlacement` (same as marker)

### Slope Analysis Entities

**Slope Change Markers:**
- `IfcBuildingElementProxy` with circular geometry
- Property set including: FromGradePercent, ToGradePercent, GradeChange, HeightAboveDatum, ChangeType

**Directional Arrows:**
- `IfcBuildingElementProxy` with arrow geometry oriented along alignment
- Property set including: GradePercent, GradeDecimal, SlopeDirection, HeightAboveDatum

### Property Sets

**Station Markers** include `Pset_StationText` with:
- `StationValue` (Real) - Exact station value
- `DisplayText` (Label) - Text shown on marker
- `TextHeight` (LengthMeasure) - Configurable
- `MarkerType` (Label) - "Triangle" or "Circle-End/Start"
- `Height`/`Radius` and `Thickness` (LengthMeasure)
- `Color` (Label) - "Green" or "Red"
- `StationName` (Label) - Original referent name

**Slope Change Markers** include `Pset_SlopeInformation` with:
- `StationNumber` (Real) - Station location
- `FromGradePercent` / `ToGradePercent` (Real) - Grade percentages
- `FromGradeDecimal` / `ToGradeDecimal` (Real) - Grade as decimal
- `GradeChange` (Real) - Change in grade (percent)
- `HeightAboveDatum` (LengthMeasure) - Elevation
- `ChangeType` (Label) - "curve", "transition", or "known"
- `MarkerColor` (Label) - "Orange"

**Directional Arrows** include `Pset_SlopeInformation` with:
- `StationNumber` (Real) - Station location
- `GradePercent` / `GradeDecimal` (Real) - Current grade
- `HeightAboveDatum` (LengthMeasure) - Elevation
- `SlopeDirection` (Label) - "Upward" or "Downward"
- `ArrowColor` (Label) - "Green" or "Red"
- `SegmentType` (Label) - "intermediate"

## Viewer Compatibility

### IfcTextLiteral Support (Modern Viewers)
- ✅ Displays styled text with proper font and size
- ✅ Best visual appearance
- ⚠️ Not supported by all IFC viewers

### Polyline Text Fallback (Universal)
- ✅ Works in all IFC viewers
- ✅ Guaranteed visibility
- ℹ️ Basic line-based text rendering

Both methods are created simultaneously, ensuring maximum compatibility.

## Project Files

### Main Scripts
- **`create_alignment_markers_oop.py`** - Unified OOP script for station markers and slope analysis
- **`geometry_markers.py`** - Shared geometry classes (triangles, circles, arrows, text)

### Input/Output Files
- **`m_f-veg_CL-1000.ifc`** - Example input IFC file with alignment data
- **`m_f-veg_CL-1000_with_markers.ifc`** - Output file with markers and optional slope analysis

### Documentation
- **`README.md`** - This file (main documentation)
- **`OOP_README.md`** - Detailed OOP architecture documentation
- **`Station_Markers_Summary.md`** - Development history and implementation details

## Advanced Usage

### Using the System as a Library

```python
from create_alignment_markers_oop import create_alignment_markers

# Custom configuration
config = {
    'triangle_height': 0.8,
    'circle_radius': 0.6,
    'marker_height_offset': 1.0,
    'text_height': 1.2,
    # ... other parameters
}

# Create markers with custom config
create_alignment_markers(
    input_file="my_alignment.ifc",
    output_file="my_alignment_with_markers.ifc",
    add_slope_analysis=True,
    **config
)
```

### Adding Custom Marker Types

To extend the system with new marker types:

1. **Create a new geometry class** in `geometry_markers.py`:
```python
class DiamondMarker(BaseMarker):
    def create_geometry(self):
        # Implement diamond shape
        pass
```

2. **Add factory method** in `create_alignment_markers_oop.py`:
```python
def create_diamond_marker(self, station_value, placement):
    geometry = DiamondMarker(self.model, ...)
    marker_element = MarkerElement(...)
    return marker_element
```

3. **Update processor logic** to use new marker type as needed.

See `OOP_README.md` for detailed architecture documentation.

## Benefits of Object-Oriented Design

### Modularity
- Geometry classes separated from business logic
- Easy to test individual components
- Clear responsibilities for each class

### Extensibility
- Add new marker types by extending `BaseMarker`
- New analysis features without modifying existing code
- Plugin-style architecture for future enhancements

### Reusability
- `geometry_markers.py` can be used in other IFC projects
- Shared placement and text utilities
- Factory pattern allows different configurations

### Maintainability
- Changes localized to specific classes
- Clear interfaces and documentation
- Type hints and docstrings throughout

## Technical Details

### Coordinate System
- Uses existing `IfcReferent` placements as reference
- Calculates alignment direction from referent RefDirection
- Calculates perpendicular direction (90° rotation in XY plane)
- Applies Z-offset for vertical positioning above alignment

### Geometry Generation
- **Triangles**: `IfcArbitraryClosedProfileDef` with 3 vertices, extruded perpendicular to alignment
- **Circles**: `IfcCircle` profile, extruded perpendicular to alignment (or along alignment for slope markers)
- **Arrows**: Triangular profile pointing in +X direction, oriented along alignment for slope indicators
- **Text**: Character-by-character polyline generation for fallback compatibility

### Placement Strategies
- **Station Markers**: RefDirection = perpendicular to alignment (markers stand across the line)
- **Slope Change Circles**: RefDirection = perpendicular to alignment (vertical disks across the line)
- **Directional Arrows**: RefDirection = along alignment (arrows point forward with increasing stations)
- All use `PlacementRelTo` for relative positioning from referents

### Color Application
- `IfcColourRgb` for RGB color definition
- `IfcSurfaceStyleRendering` for surface appearance
- `IfcStyledItem` to apply styles to geometry
- Transparency support for slope change markers

## License

This project is provided as-is for IFC alignment visualization purposes.

## Contributing

To improve or extend functionality:
1. Add new marker types by extending `BaseMarker` class in `geometry_markers.py`
2. Enhance slope detection algorithms in `SlopeChangeDetector`
3. Add new analysis features to `AlignmentMarkerProcessor`
4. Implement additional property sets for metadata
5. Create unit tests for classes
6. Add type hints and improve documentation

For detailed architecture information, see `OOP_README.md`.

## Support

For IFC-related questions, refer to:
- [buildingSMART IFC Documentation](https://standards.buildingsmart.org/IFC)
- [IfcOpenShell Documentation](http://ifcopenshell.org/)
