class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

class Address:
    def __init__(self, city, zip_code):
        self.city = city
        self.zip_code = zip_code

people = [Person("Alice", 25), Person("Bob", 30)]
addresses = [Address("New York", "10001"), Address("San Francisco", "94105")]

for person, address in zip(people, addresses):
    print("Name:", person.name, "Age:", person.age, "City:", address.city, "Zip Code:", address.zip_code)
