import mlconjug3

# Test the actual structure returned by mlconjug3
fr_conjugator = mlconjug3.Conjugator(language='fr')
es_conjugator = mlconjug3.Conjugator(language='es')

print("=== FRENCH TEST ===")
fr_verb = fr_conjugator.conjugate('parler')
print(f"Type of fr_verb: {type(fr_verb)}")
print(f"Fr_verb object: {fr_verb}")

print("\n--- French iterate() method ---")
for i, item in enumerate(fr_verb.iterate()):
    print(f"Item {i}: {item} (type: {type(item)})")
    if i >= 5:  # Just show first few items
        break

print("\n=== SPANISH TEST ===")
es_verb = es_conjugator.conjugate('hablar')
print(f"Type of es_verb: {type(es_verb)}")
print(f"Es_verb object: {es_verb}")

print("\n--- Spanish iterate() method ---")
for i, item in enumerate(es_verb.iterate()):
    print(f"Item {i}: {item} (type: {type(item)})")
    if i >= 5:  # Just show first few items
        break
