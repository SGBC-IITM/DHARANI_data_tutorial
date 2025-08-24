import numpy as np
from shapely.geometry import Polygon, LineString

def morph_contour(
    from_poly: Polygon, to_poly: Polygon, num_points: int = 100
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """
    Generates a correspondence set between the contours of two polygons.

    This function takes two Shapely polygons and creates a mapping of points
    from the exterior of the first polygon to the exterior of the second.
    It does this by sampling a specified number of equidistant points along
    the normalized length of each polygon's exterior contour.

    Args:
        from_poly: The starting polygon for the morph.
        to_poly: The target polygon for the morph.
        num_points: The number of corresponding points to generate.

    Returns:
        A tuple containing two lists of (x, y) coordinate tuples. The first
        list contains points on the `from_poly` contour, and the second list
        contains the corresponding points on the `to_poly` contour.
    """
    from_contour = from_poly.exterior
    to_contour = to_poly.exterior

    from_points = []
    to_points = []

    for i in np.linspace(0, 1, num_points):
        # Interpolate point along the normalized distance of the contour
        from_point = from_contour.interpolate(i, normalized=True)
        to_point = to_contour.interpolate(i, normalized=True)

        from_points.append((from_point.x, from_point.y))
        to_points.append((to_point.x, to_point.y))

    return from_points, to_points

if __name__ == "__main__":
    # Create two simple polygons for demonstration
    poly1 = Polygon([(0, 0), (1, 5), (5, 5), (5, 0), (0, 0)])
    poly2 = Polygon([(3, 3), (3, 6), (6, 6), (6, 3), (3, 3)])

    # Generate the correspondence set
    from_pts, to_pts = morph_contour(poly1, poly2, num_points=10)

    # Print the results
    print("From Contour Points:")
    for p in from_pts:
        print(f"  ({p[0]:.2f}, {p[1]:.2f})")

    print("\nTo Contour Points:")
    for p in to_pts:
        print(f"  ({p[0]:.2f}, {p[1]:.2f})")

    # Verify the number of points
    assert len(from_pts) == 10
    assert len(to_pts) == 10

    print("\nSuccessfully generated 10 correspondence points.")
