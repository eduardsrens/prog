def count_evens_dalit(numbers: list[int]) -> int:
#Pāra skaitļu noteikšana ar dalījuma atlikumu (%)
    count = 0
    for num in numbers:
        if num % 2 == 0:
            count += 1
    return count


def count_evens_biti(numbers: list[int]) -> int:
#Pāra skaitļu noteikšana ar bitu operāciju (&)
    count = 0
    for num in numbers:
        if (num & 1) == 0:
            count += 1
    return count
