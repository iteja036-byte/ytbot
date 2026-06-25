from validator import validate_and_fix

data = validate_and_fix("captions.json")

if not data:
    print("STOP: invalid data")
    exit(1)

print("READY FOR YTBOT BRAIN")
print(data)
