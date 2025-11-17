# IFC Station Markers Generator

Automatically generate visual station markers and text labels along alignment centerlines in IFC files.

This image show the result in Trimble Connect Online Viewer. The result in other viewers may be different due to different support of IfcAnnotation and IfcTextLiteral.

<img width="855" height="769" alt="image" src="https://github.com/user-attachments/assets/c524af4f-6d07-42a3-85f8-ba4c870ba6e9" />

This is the same file in Blender/Bonsai (0.8.3 post1)
<img width="592" height="499" alt="image" src="https://github.com/user-attachments/assets/bd78ddb6-304d-47b6-acde-4acd8ed02f22" />

This is the same file in BIMvision display IfcTextLiteral alongside the IfcAnnotation (only visible after double clicking on the annotation object in the ifc file tree.

<img width="578" height="480" alt="image" src="https://github.com/user-attachments/assets/219b4f75-b051-441b-b146-cb18c60cfe46" />

## Overview

This project provides a Python script that reads an IFC file containing alignment data with `IfcReferent` objects and creates visible station markers with text labels. The script generates both geometric markers (triangles/circles) and text annotations at each station point.

## Features

- **Dual Marker Types**:
  - 🔺 **Green triangles** for intermediate stations (0.5m high, 1cm thick)
  - 🔴 **Red circles** for start/end stations (0.5m radius, 1cm thick)
  
- **Dual Text Representation** (maximum compatibility):
  - `IfcTextLiteral` with `IfcTextStyle` - Modern styled text for advanced viewers
  - `IfcAnnotation` with polyline geometry - Fallback for basic viewers
  
- **Smart Positioning**:
  - Markers positioned 0.5m above the alignment line
  - Automatic perpendicular orientation to alignment direction
  - Text labels scaled to 0.5m height for visibility

- **Color Coded**:
  - Start/End stations: Red circles
  - Intermediate stations: Green triangles

## Requirements

```bash
pip install ifcopenshell
```

## Usage

### Basic Usage

```python
python create_text_markers.py
```

The script will:
1. Read from `m_f-veg_CL-1000.ifc` (input file)
2. Process all `IfcReferent` objects (station points)
3. Create markers and text annotations
4. Save to `m_f-veg_CL-1000_with_text.ifc` (output file)

### Customizing Input/Output Files

Edit the `__main__` section in `create_text_markers.py`:

```python
if __name__ == "__main__":
    input_file = "your_input_file.ifc"
    output_file = "your_output_file.ifc"
    
    create_text_markers(input_file, output_file)
```

## Output

The script generates **2 IFC elements per station**:

1. **IfcBuildingElementProxy** - Contains:
   - Triangle or circle geometry (colored)
   - IfcTextLiteral with styling (modern text)
   - Property set with station metadata

2. **IfcAnnotation** - Contains:
   - Polyline-based text geometry (fallback)
   - Same positioning as marker

### Example Output

For a file with 24 stations (0, 10, 20, ..., 220, 228.6):
- **48 total elements** created (24 markers + 24 text annotations)
- **2 red circles** at stations 0 and 228.6
- **22 green triangles** at stations 10 through 220

## Marker Specifications

### Triangle Markers (Intermediate Stations)
- **Height**: 0.5 meters (base at line, tip pointing up)
- **Thickness**: 0.01 meters (1 cm)
- **Color**: Green RGB(0.0, 0.8, 0.0)
- **Orientation**: Perpendicular to alignment direction
- **Position**: Base 0.5m above alignment

### Circle Markers (Start/End Stations)
- **Radius**: 0.5 meters
- **Thickness**: 0.01 meters (1 cm)
- **Color**: Red RGB(1.0, 0.0, 0.0)
- **Orientation**: Vertical plane
- **Position**: Center 0.5m above alignment

### Text Labels
- **Height**: 0.5 meters
- **Font**: Arial (for IfcTextLiteral)
- **Color**: Black
- **Content**: Station value (e.g., "0", "10", "100", "228.6")
- **Format**: Integer display for whole numbers, one decimal for fractional values

## IFC Structure

### Entities Created

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

### Property Sets

Each marker includes `Pset_StationText` with:
- `StationValue` (Real) - Exact station value
- `DisplayText` (Label) - Text shown on marker
- `TextHeight` (LengthMeasure) - 0.5m
- `TriangleHeight` or `CircleRadius` (LengthMeasure)
- `TriangleThickness` or `CircleThickness` (LengthMeasure)
- `MarkerType` (Label) - "TriangleMarker" or "CircleMarker"
- `Color` (Label) - "Green" or "Red"
- `StationName` (Label) - Original referent name
- `ViewDirection` (Label) - "TopDown"

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

## Technical Details

### Coordinate System
- Uses existing `IfcReferent` placements as reference
- Calculates perpendicular direction from alignment
- Applies Z-offset for vertical positioning

### Geometry Generation
- **Triangles**: `IfcArbitraryClosedProfileDef` with 3 vertices
- **Circles**: `IfcCircle` with specified radius
- **Extrusion**: 1cm thickness in perpendicular direction
- **Text**: Character-by-character polyline generation

### Color Application
- `IfcColourRgb` for RGB color definition
- `IfcSurfaceStyleShading` for surface rendering
- `IfcStyledItem` to apply color to geometry

## Files

- `create_text_markers.py` - Main script
- `m_f-veg_CL-1000.ifc` - Input IFC file
- `m_f-veg_CL-1000_with_text.ifc` - Output IFC file
- `Station_Markers_Summary.md` - Detailed summary of implementation
- `README.md` - This file

## Script Functions

### `generate_ifc_guid()`
Generates unique IFC-compliant GUIDs for new entities.

### `create_triangle_geometry(model, height=0.5, thickness=0.01)`
Creates vertical triangle geometry with specified dimensions.

### `create_circle_geometry(model, radius=0.5, thickness=0.01)`
Creates circular disk geometry with specified dimensions.

### `create_text_geometry(model, text_content, height=5.0, width_factor=0.6)`
Generates polyline-based text characters for fallback rendering.

### `create_text_markers(input_file, output_file)`
Main function that:
1. Loads IFC file
2. Finds all `IfcReferent` objects
3. Determines start/end stations (min/max values)
4. Creates appropriate marker type
5. Adds dual text representations
6. Saves modified IFC file

## Customization

All parameters are now easily configurable in the `__main__` section of each script. Simply edit the values at the top of the file before running.

### create_text_markers.py - Configurable Parameters

Edit the `USER CONFIGURABLE PARAMETERS` section at the bottom of `create_text_markers.py`:

```python
# Triangle Marker Settings (for intermediate stations)
TRIANGLE_HEIGHT = 0.5           # Height in meters
TRIANGLE_THICKNESS = 0.01       # Thickness in meters
TRIANGLE_COLOR = (0.0, 0.8, 0.0)  # RGB (Green)

# Circle Marker Settings (for start/end stations)
CIRCLE_RADIUS = 0.5             # Radius in meters
CIRCLE_THICKNESS = 0.01         # Thickness in meters
CIRCLE_COLOR = (1.0, 0.0, 0.0)  # RGB (Red)

# Text Settings
TEXT_HEIGHT = 1.0               # Height in meters
TEXT_WIDTH_FACTOR = 0.6         # Width-to-height ratio
TEXT_COLOR = (0.0, 0.0, 0.0)    # RGB (Black)

# Positioning Settings
MARKER_HEIGHT_OFFSET = 0.5      # Vertical offset above alignment
TEXT_POSITION_OFFSET = (0.0, 0.2, 0.0)  # XYZ offset for text
```

### add_slope_information.py - Configurable Parameters

Edit the `USER CONFIGURABLE PARAMETERS` section at the bottom of `add_slope_information.py`:

```python
# Slope Change Marker Settings
SLOPE_MARKER_RADIUS = 0.4           # Radius in meters
SLOPE_MARKER_THICKNESS = 0.06       # Thickness in meters
SLOPE_MARKER_COLOR = (1.0, 0.5, 0.0)  # RGB (Orange)

# Directional Arrow Settings
ARROW_LENGTH = 0.6                  # Length in meters
ARROW_WIDTH = 0.3                   # Width in meters
ARROW_THICKNESS = 0.05              # Thickness in meters
ARROW_COLOR_POSITIVE = (0.0, 0.8, 0.0)  # RGB (Green for upward)
ARROW_COLOR_NEGATIVE = (1.0, 0.0, 0.0)  # RGB (Red for downward)

# Text Settings
TEXT_HEIGHT_LARGE = 0.6             # Large text height
TEXT_HEIGHT_MEDIUM = 0.5            # Medium text height
TEXT_HEIGHT_SMALL = 0.4             # Small text height
TEXT_COLOR = (0.0, 0.0, 0.8)        # RGB (DarkBlue)
TEXT_FONT = "Arial"                 # Font family

# Positioning Settings
SLOPE_MARKER_HEIGHT_OFFSET = 1.0    # Vertical offset for slope markers
ARROW_HEIGHT_OFFSET = 0.8           # Vertical offset for arrows
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

**Change Color Scheme to Blue/Yellow:**
```python
TRIANGLE_COLOR = (0.0, 0.0, 1.0)  # Blue
CIRCLE_COLOR = (1.0, 1.0, 0.0)    # Yellow
```

**Position Markers Higher Above Alignment:**
```python
MARKER_HEIGHT_OFFSET = 1.5  # 1.5m instead of 0.5m
```

## Development History

The script evolved through several iterations:
1. Initial box-based markers
2. Triangle geometry with orientation refinement
3. Color coding for start/end stations
4. IfcTextLiteral implementation with styling
5. Polyline text fallback method
6. Separation of text into IfcAnnotation entities (current version)

See `Station_Markers_Summary.md` for complete development history.

## License

This project is provided as-is for IFC alignment visualization purposes.

## Contributing

To improve or extend functionality:
1. Modify marker geometry in `create_triangle_geometry()` or `create_circle_geometry()`
2. Enhance text rendering in `create_text_geometry()`
3. Add new marker types for specific station conditions
4. Implement additional property sets for metadata

## Support

For IFC-related questions, refer to:
- [buildingSMART IFC Documentation](https://standards.buildingsmart.org/IFC)
- [IfcOpenShell Documentation](http://ifcopenshell.org/)
