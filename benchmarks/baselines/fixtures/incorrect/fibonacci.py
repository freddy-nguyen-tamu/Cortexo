def fibonacci(n):
    if n <= 0:
        return []
    if n == 1:
        return [0]
    values = [0, 1]
    while len(values) < n:
        values.append(values[-1] + values[-2])
    return values[:n]