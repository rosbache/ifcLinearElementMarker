#!/usr/bin/env python3
"""
IFC Area Calculator
Calculates surface areas from triangulated face sets and updates C004 Areal properties
"""

import ifcopenshell
import numpy as np
import sys
import os

def calculate_triangle_area(p1, p2, p3):
    """
    Calculate the area of a triangle given three 3D points using cross product
    """
    # Convert to numpy arrays for easier calculation
    v1 = np.array(p2) - np.array(p1)
    v2 = np.array(p3) - np.array(p1)
    
    # Cross product gives a vector whose magnitude is twice the triangle area
    cross = np.cross(v1, v2)
    
    # For 3D vectors, cross product is a vector, so we need its magnitude
    if cross.ndim > 0:
        area = 0.5 * np.linalg.norm(cross)
    else:
        area = 0.5 * abs(cross)
    
    return area

def calculate_triangulated_faceset_area(faceset, point_list):
    """
    Calculate total area of an IFCTRIANGULATEDFACESET
    """
    total_area = 0.0
    
    # Get the coordinate indices (triangles)
    coord_index = faceset.CoordIndex
    coordinates = point_list.CoordList
    
    # Calculate area for each triangle
    for triangle in coord_index:
        # IFC indices are 1-based, convert to 0-based
        p1_idx, p2_idx, p3_idx = triangle[0] - 1, triangle[1] - 1, triangle[2] - 1
        
        # Get the 3D coordinates
        p1 = coordinates[p1_idx]
        p2 = coordinates[p2_idx] 
        p3 = coordinates[p3_idx]
        
        # Calculate triangle area and add to total
        triangle_area = calculate_triangle_area(p1, p2, p3)
        total_area += triangle_area
    
    return total_area

def find_geometry_for_element(model, element):
    """
    Find the geometry representation for an IFC element
    """
    if not hasattr(element, 'Representation') or not element.Representation:
        return None
    
    # Navigate through the representation structure
    for representation in element.Representation.Representations:
        if hasattr(representation, 'Items'):
            for item in representation.Items:
                if item.is_a('IfcTriangulatedFaceSet'):
                    return item
    
    return None

def update_area_properties(ifc_file_path, output_file_path=None):
    """
    Main function to update C004 Areal properties in the IFC file
    """
    print(f"Loading IFC file: {ifc_file_path}")
    
    # Load the IFC file
    model = ifcopenshell.open(ifc_file_path)
    
    # Find all property single values with C004 Areal
    c004_properties = []
    for prop in model.by_type('IfcPropertySingleValue'):
        if prop.Name == 'C004 Areal (topp volum)':
            c004_properties.append(prop)
    
    print(f"Found {len(c004_properties)} C004 Areal properties")
    
    # Keep track of updates
    updates_made = 0
    
    # For each C004 property, find the associated element and calculate its area
    for prop in c004_properties:
        # Find the property set that contains this property
        prop_sets = [ps for ps in model.by_type('IfcPropertySet') if prop in ps.HasProperties]
        
        for prop_set in prop_sets:
            # Find elements that reference this property set
            rel_defines = [rd for rd in model.by_type('IfcRelDefinesByProperties') 
                          if rd.RelatingPropertyDefinition == prop_set]
            
            for rel_define in rel_defines:
                for element in rel_define.RelatedObjects:
                    print(f"Processing element: {element.Name or element.GlobalId}")
                    
                    # Find geometry for this element
                    geometry = find_geometry_for_element(model, element)
                    
                    if geometry and geometry.is_a('IfcTriangulatedFaceSet'):
                        # Calculate the area
                        area = calculate_triangulated_faceset_area(geometry, geometry.Coordinates)
                        
                        print(f"  Calculated area: {area:.6f} m²")
                        
                        # Update the property value
                        if area > 0:
                            prop.NominalValue = model.create_entity('IfcReal', area)
                            updates_made += 1
                            print(f"  ✓ Updated C004 Areal property to {area:.6f}")
                        else:
                            print("  ⚠ Area is 0, property not updated")
                    else:
                        print("  ⚠ No triangulated geometry found for element")
    
    print(f"\nTotal updates made: {updates_made}")
    
    # Save the modified file
    if output_file_path is None:
        # Create output filename by adding _area_updated before extension
        base_name = os.path.splitext(ifc_file_path)[0]
        extension = os.path.splitext(ifc_file_path)[1]
        output_file_path = f"{base_name}_area_updated{extension}"
    
    print(f"Saving updated file to: {output_file_path}")
    model.write(output_file_path)
    
    return output_file_path, updates_made

def main():
    """
    Command line interface
    """
    if len(sys.argv) < 2:
        print("Usage: python calculate_ifc_areas.py <input_ifc_file> [output_ifc_file]")
        print("If no output file is specified, '_area_updated' will be added to the input filename")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist")
        sys.exit(1)
    
    try:
        output_path, updates = update_area_properties(input_file, output_file)
        print("\n✓ Successfully processed file!")
        print(f"  Input:  {input_file}")
        print(f"  Output: {output_path}")
        print(f"  Properties updated: {updates}")
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()