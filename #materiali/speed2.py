def bubble_sort(arr: list[int]) -> list[int]:
#Burbuļa kārtošana - O(n^2)
    data = arr.copy()
    n = len(data)
    for i in range(n):
        for j in range(0, n - i - 1):
            if data[j] > data[j + 1]:
                data[j], data[j + 1] = data[j + 1], data[j]
    return data


def quick_sort(arr: list[int]) -> list[int]:
#Ātrā kārtošana (Quicksort) - O(n log n)
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)