# Object-Oriented IFC Marker System

This is a refactored, object-oriented version of the IFC station marker and slope analysis system.

## Architecture Overview

The system is organized into three main modules:

### 1. `geometry_markers.py` - Geometry Classes

Contains the core geometry and marker classes:

#### Base Classes
- **`BaseMarker`** - Abstract base class for all marker geometries
  - Provides common functionality for creating IFC geometry, colors, and styles
  - Enforces interface through abstract methods
  - Handles IFC entity creation for colors and styling

#### Marker Types
- **`TriangleMarker`** - Green triangular markers for intermediate stations
  - Inherits from `BaseMarker`
  - Creates triangular profile with configurable height and thickness
  - Default color: Green (0.0, 0.8, 0.0)

- **`CircleMarker`** - Red circular markers for start/end stations
  - Inherits from `BaseMarker`
  - Creates circular profile with configurable radius and thickness
  - Default color: Red (1.0, 0.0, 0.0)

- **`DirectionalArrow`** - Directional arrows for slope indication
  - Inherits from `BaseMarker`
  - Creates arrow profile pointing in alignment direction
  - Color based on slope direction (green=upward, red=downward)

#### Wrapper Classes
- **`MarkerElement`** - Wraps geometry with properties and IFC element creation
  - Manages property sets
  - Creates IFC BuildingElementProxy elements
  - Handles relationship between geometry and properties

- **`TextAnnotation`** - Creates polyline-based text rendering
  - Character definitions as polyline coordinates
  - Fallback text representation for IFC viewers

### 2. `create_text_markers_oop.py` - Main Application

Contains high-level orchestration classes:

#### Factory Pattern
- **`StationMarkerFactory`** - Creates marker instances based on station type
  - Centralizes marker creation logic
  - Applies standard properties
  - Encapsulates marker configuration

#### Helper Classes
- **`PlacementCalculator`** - Calculates spatial placements
  - Determines perpendicular directions to alignment
  - Creates IFC placements with correct orientations
  - Handles coordinate transformations

- **`TextLiteralCreator`** - Creates IFC text representations
  - IfcTextLiteral with styling (modern approach)
  - Polyline-based fallback text (compatibility)
  - Font and color management

#### Main Processor
- **`StationMarkerProcessor`** - Main orchestration class
  - Processes all referents in IFC model
  - Coordinates factory, placement, and text creation
  - Manages spatial structure relationships
  - Handles IFC file I/O

### 3. `add_slope_information_oop.py` - Slope Analysis Application

Contains slope analysis and marker creation classes:

#### Detection and Analysis
- **`SlopeChangeDetector`** - Detects slope change points in alignment
  - Analyzes vertical alignment segments
  - Identifies grade transitions and curve endpoints
  - Supports known slope change points
  - Configurable change threshold

#### Factory Pattern
- **`SlopeMarkerFactory`** - Creates slope-related markers
  - Creates orange circle markers for slope changes
  - Creates directional arrows (green/red) for slope direction
  - Applies comprehensive property sets
  - Manages color coding based on slope direction

#### Helper Classes
- **`TextLiteralCreator`** - Creates styled IfcTextLiteral annotations
  - Configurable fonts, colors, and sizes
  - Bold/normal font weight support
  - Consistent styling across all text

- **`PlacementCalculator`** - Spatial calculations (shared with station markers)
  - Perpendicular direction calculations
  - Position extraction from placements
  - Offset placement creation

#### Main Processor
- **`SlopeAnalysisProcessor`** - Main orchestration for slope analysis
  - Extracts vertical alignment segments
  - Builds referent mapping
  - Processes slope changes with markers
  - Adds directional arrows at stations
  - Creates segment boundary labels
  - Manages spatial structure and IFC relationships
  - Generates comprehensive summary reports

## Benefits of This Architecture

### 1. **Separation of Concerns**
- Geometry creation separated from business logic
- Placement calculations isolated from marker creation
- Text handling independent from geometry

### 2. **Extensibility**
- Easy to add new marker types (diamond, hexagon, etc.)
- New properties can be added without changing geometry
- Text rendering can be enhanced independently

### 3. **Testability**
- Each class can be unit tested independently
- Mock objects can be used for testing
- Clear interfaces make testing easier

### 4. **Reusability**
- Geometry classes can be used in other IFC projects
- Factory pattern allows different marker configurations
- Placement calculator useful for any IFC alignment work

### 5. **Maintainability**
- Changes to geometry don't affect placement logic
- Bug fixes localized to specific classes
- Clear responsibility for each class

## Usage Example

```python
from geometry_markers import TriangleMarker, CircleMarker, MarkerElement

# Create model and get context (from existing IFC)
model = ifcopenshell.open("input.ifc")
owner_history = model.by_type("IfcOwnerHistory")[0]
context_3d = model.by_type("IfcGeometricRepresentationContext")[0]

# Create a triangle marker
triangle_geom = TriangleMarker(model, height=0.5, thickness=0.05)
marker = MarkerElement(model, triangle_geom, owner_history, context_3d)

# Add custom properties
marker.add_property("StationValue", 100.0)
marker.add_property("Description", "Station marker at 100m")

# Create IFC element
element = marker.create_ifc_element(
    name="Station_100",
    description="Marker at station 100",
    placement=placement_obj
)
```

## Class Diagram

```
BaseMarker (Abstract)
    │
    ├── TriangleMarker (station markers)
    ├── CircleMarker (start/end stations, slope changes)
    └── DirectionalArrow (slope direction indicators)

MarkerElement
    └── wraps BaseMarker instances

StationMarkerFactory
    └── creates station marker elements

SlopeMarkerFactory
    └── creates slope marker elements

SlopeChangeDetector
    └── analyzes vertical alignment

PlacementCalculator
    └── static utility methods

TextLiteralCreator
    └── creates styled text representations

TextAnnotation
    └── creates polyline-based text fallback

StationMarkerProcessor
    ├── uses StationMarkerFactory
    ├── uses PlacementCalculator
    └── uses TextLiteralCreator

SlopeAnalysisProcessor
    ├── uses SlopeMarkerFactory
    ├── uses SlopeChangeDetector
    ├── uses PlacementCalculator
    └── uses TextLiteralCreator
```

## Configuration

All user-configurable parameters are in configuration dictionaries:

### Station Markers (`create_text_markers_oop.py`)
```python
config = {
    'triangle_height': 0.5,
    'triangle_thickness': 0.01,
    'triangle_color': (0.0, 0.8, 0.0),  # Green
    'circle_radius': 0.5,
    'circle_thickness': 0.01,
    'circle_color': (1.0, 0.0, 0.0),  # Red
    'text_height': 1.0,
    'text_width_factor': 0.6,
    'text_color': (0.0, 0.0, 0.0),  # Black
    'marker_height_offset': 0.5,
    'text_position_offset': (0.0, 0.2, 0.0)
}
```

### Slope Analysis (`add_slope_information_oop.py`)
```python
config = {
    'slope_marker_radius': 0.4,
    'slope_marker_thickness': 0.05,
    'slope_marker_color': (1.0, 0.5, 0.0),  # Orange
    'slope_marker_height_offset': 0.5,
    'arrow_length': 0.5,
    'arrow_width': 0.25,
    'arrow_thickness': 0.05,
    'arrow_height_offset': 0.8,
    'text_height_large': 0.6,
    'text_height_medium': 0.5,
    'text_height_small': 0.4,
    'text_color': (0.0, 0.0, 0.8),  # Dark blue
    'text_font': "Arial",
    'property_set_name': "Pset_SlopeInformation",
    'grade_change_threshold': 0.01  # 1% minimum
}
```

## Running the OOP Version

### Station Markers
```bash
python create_text_markers_oop.py
```

### Slope Analysis
```bash
python add_slope_information_oop.py
```

Both scripts use configuration dictionaries for easy customization.

## Adding New Marker Types

To add a new marker type (e.g., diamond):

1. **Create geometry class** in `geometry_markers.py`:
```python
class DiamondMarker(BaseMarker):
    def __init__(self, model, size=0.5, thickness=0.05, color=(0.0, 0.0, 1.0)):
        super().__init__(model, color, thickness)
        self.size = size
    
    def get_default_color_name(self):
        return "Blue"
    
    def create_geometry(self):
        # Create diamond profile
        # ... implementation
        pass
```

2. **Add factory method** in `create_text_markers_oop.py`:
```python
def create_diamond_marker(self, station_value, placement, size=0.5):
    geometry = DiamondMarker(self.model, size)
    marker_element = MarkerElement(...)
    return marker_element
```

3. **Use in processor** as needed.

## Comparison with Procedural Version

| Aspect | Procedural | OOP |
|--------|-----------|-----|
| Code organization | Functions | Classes with clear responsibilities |
| Extensibility | Modify functions | Add new classes |
| Testing | Test entire flow | Test individual components |
| Reusability | Copy/paste functions | Import and instantiate classes |
| Configuration | Function parameters | Config dictionaries |
| Property management | Ad-hoc | Centralized in MarkerElement |
| Slope detection | Inline logic | SlopeChangeDetector class |
| Multiple scripts | Separate procedural files | Shared geometry_markers module |

## Files Overview

### OOP Version
- **`geometry_markers.py`** - Shared geometry classes (576 lines)
- **`create_text_markers_oop.py`** - Station markers (647 lines)
- **`add_slope_information_oop.py`** - Slope analysis (873 lines)
- **`OOP_README.md`** - Documentation

### Procedural Version (for reference)
- **`create_text_markers.py`** - Station markers (498 lines)
- **`add_slope_information.py`** - Slope analysis (951 lines)

The OOP version has better code organization despite similar total line count, with shared functionality in `geometry_markers.py` reducing duplication.

## Future Enhancements

Possible improvements to the OOP architecture:

1. **Strategy Pattern** for different placement algorithms
2. **Builder Pattern** for complex marker configurations
3. **Observer Pattern** for progress reporting
4. **Composite Pattern** for grouped markers
5. **Repository Pattern** for IFC model access
6. **Command Pattern** for undoable operations
7. **Unified slope+station workflow** in single script
8. **Configuration file support** (JSON/YAML)
9. **Unit tests** for all classes
10. **Type hints** throughout codebase

