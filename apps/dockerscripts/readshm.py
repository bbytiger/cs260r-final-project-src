f = open("test.txt", "r")
contents = f.read()
print(f"recv reading from {__file__}...")
print(f"recv data: {contents}")
f.close()
