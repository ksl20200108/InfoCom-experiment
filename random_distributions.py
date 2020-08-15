import random

def transaction_fee():
    return random.uniform(0.1, 0.6)

def pdf_distribution():
    pass    # open and store txt

def result1():
    print("python3 cli.py send --from 1EiVGWYsWiM7shgR5i9KTE2kUjzqcyQU9W --to 1CjsJ3JguwfGRAW1CKgVYor4UgcSG2XF9n --amount 1 --fee %f" % transaction_fee())
    print("")

for i in range(1, 51):
    print("experiment %d" % i)
    print("")
    for j in range(1, 12):
        result1()
