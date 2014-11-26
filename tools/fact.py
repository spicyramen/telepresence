def factorial(num):
    print "Factorial of " + str(num)
    if num == 1 or num == 0:
        return 1
    total = 1
    
    for index in range(1, num+1):
	total = total * index
    	print "Total is: " + str(total) + " index: " + str(index)
    return total
    
x = factorial(5)
print x
