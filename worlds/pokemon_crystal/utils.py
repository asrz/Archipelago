from .data import data


def get_random_pokemon(random, types=None):
    pokemon_pool = []
    if types is None or types[0] is None:
        pokemon_pool = [pkmn_name for pkmn_name, _data in data.pokemon.items() if pkmn_name != "UNOWN"]
    else:
        pokemon_pool = [pkmn_name for pkmn_name, pkmn_data in data.pokemon.items()
                        if pkmn_name != "UNOWN" and pkmn_data.types == types]
    return random.choice(pokemon_pool)

def get_random_pokemon_by_type(random, poke_type):
    pokemon_pool = [pkmn_name for pkmn_name, pkmn_data in data.pokemon.items()
                    if pkmn_name != "UNOWN" and poke_type in pkmn_data.types]
    return random.choice(pokemon_pool)

def get_random_pokemon_id(random):
    pokemon_pool = [i for i in range(1, 251) if i != 0xC9]
    return random.choice(pokemon_pool)

def get_random_type(random):
    return random.choice(data.types)
