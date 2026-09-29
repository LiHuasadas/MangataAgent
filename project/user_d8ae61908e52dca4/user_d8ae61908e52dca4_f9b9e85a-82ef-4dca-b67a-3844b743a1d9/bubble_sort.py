def bubble_sort(arr):
    """Bubble sort implementation: O(n^2), stable, in-place on copy.
    
    Args:
        arr: list or tuple of numbers (int/float)
    Returns:
        new sorted list in ascending order
    """
    arr = list(arr)
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

if __name__ == '__main__':
    print(bubble_sort([5, 3, 1, 4, 2]))
