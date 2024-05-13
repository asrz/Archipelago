import settings
from typing import List, Union, ClassVar, Dict, Any, Tuple
import copy

from BaseClasses import Tutorial, ItemClassification
from Fill import fill_restrictive, FillError
from worlds.AutoWorld import World, WebWorld
from .client import PokemonCrystalClient
from .options import PokemonCrystalOptions
from .regions import create_regions
from .items import PokemonCrystalItem, create_item_label_to_code_map, get_item_classification
from .rules import set_rules
from .data import (PokemonData, MoveData, TrainerData, LearnsetData, data as crystal_data)
from .rom import generate_output
from .locations import create_locations, PokemonCrystalLocation, create_location_label_to_id_map
from .utils import get_random_pokemon, get_random_type, get_random_pokemon_by_type


class PokemonCrystalSettings(settings.Group):
    class RomFile(settings.UserFilePath):
        description = "Pokemon Crystal (UE) (V1.0) ROM File"
        copy_to = "Pokemon - Crystal Version (UE) (V1.0) [C][!].gbc"
        md5s = ["9f2922b235a5eeb78d65594e82ef5dde"]

    class RomStart(str):
        """
        Set this to false to never autostart a rom (such as after patching)
        True for operating system default program
        Alternatively, a path to a program to open the .gb file with
        """

    rom_file: RomFile = RomFile(RomFile.copy_to)
    rom_start: Union[RomStart, bool] = True


class PokemonCrystalWebWorld(WebWorld):
    tutorials = [Tutorial(
        "Multiworld Setup Guide",
        "A guide to playing Pokemon Crystal with Archipelago.",
        "English",
        "setup_en.md",
        "setup/en",
        ["AliceMousie"]
    )]


class PokemonCrystalWorld(World):
    """the only good pokemon game"""
    game = "Pokemon Crystal"

    topology_present = True
    web = PokemonCrystalWebWorld()

    settings_key = "pokemon_crystal_settings"
    settings: ClassVar[PokemonCrystalSettings]

    options_dataclass = PokemonCrystalOptions
    options: PokemonCrystalOptions

    data_version = 0
    required_client_version = (0, 4, 4)

    item_name_to_id = create_item_label_to_code_map()
    location_name_to_id = create_location_label_to_id_map()
    item_name_groups = {}  # item_groups

    generated_pokemon: Dict[str, PokemonData]
    generated_starters: Tuple[List[str], List[str], List[str]]
    generated_trainers: Dict[str, TrainerData]

    def create_regions(self) -> None:
        regions = create_regions(self)
        create_locations(self, regions, self.options.randomize_hidden_items, self.options.randomize_badges)
        self.multiworld.regions.extend(regions.values())

    def create_items(self) -> None:
        item_locations: List[PokemonCrystalLocation] = [
            location
            for location in self.multiworld.get_locations(self.player)
            if location.address is not None
        ]

        default_itempool = [self.create_item_by_code(location.default_item_code) for location in item_locations]
        self.multiworld.itempool += default_itempool

    def set_rules(self) -> None:
        set_rules(self)

    def fill_hook(self, progitempool, usefulitempool, filleritempool, fill_locations):
        if self.options.randomize_hidden_items == "filler_only":
            hidden_locs = [ loc for loc in fill_locations if "Hidden" in loc.tags and loc.player == self.player ]
            
            hidden_items = self.multiworld.random.sample(filleritempool, len(hidden_locs))
            
            for item in hidden_items:
                filleritempool.remove(item)
            
            for _ in range(5):
                state = self.multiworld.get_all_state(False)
                hidden_locs_copy = hidden_locs.copy()
                self.multiworld.random.shuffle(hidden_items)
                self.multiworld.random.shuffle(hidden_locs_copy)
                
                fill_restrictive(self.multiworld, state, hidden_locs_copy, hidden_items, False, True, allow_partial=True, name="Placing Hidden Items")
                for location in hidden_locs:
                    if location.item:
                        fill_locations.remove(location)
                filleritempool += hidden_items
                break
            else:
                raise FillError(f"Failed to place hidden items for player {self.player}")
        if self.options.randomize_badges == "shuffle":
            badge_items = [ item for item in progitempool if "Badge" in item.tags and item.player == self.player ]
            badge_locs = [ loc for loc in fill_locations if "Badge" in loc.tags and loc.player == self.player ]
            
            for badge in badge_items:
                self.multiworld.itempool.remove(badge)
                progitempool.remove(badge)
            
            for _ in range(5):
                state = self.multiworld.get_all_state(False)
                self.multiworld.random.shuffle(badge_items)
                self.multiworld.random.shuffle(badge_locs)
                badge_locs_copy = badge_locs.copy()
                # allow_partial so that unplaced badges aren't lost, for debugging purposes
                fill_restrictive(self.multiworld, state, badge_locs_copy, badge_items, True, True, allow_partial=True, name="Randomizing Badges")
                if len(badge_items) > 16 - len(badge_locs):
                    for location in badge_locs:
                        if location.item:
                            badge_items.append(location.item)
                            location.item = None
                    continue
                else:
                    for location in badge_locs:
                        if location.item:
                            fill_locations.remove(location)
                    for item in badge_items:
                        if item.classification == ItemClassification.filler:
                            filleritempool.append(item)
                        elif item.classification == ItemClassification.useful:
                            usefulitempool.append(item)
                        elif item.classification == ItemClassification.progression:
                            progitempool.append(item)
                        else:
                            raise FillError(f"Unhandled ItemClassification {item.classification} for player {self.player}")
                    break
            else:
                raise FillError(f"Failed to place badges for player {self.player}")
            

    def generate_output(self, output_directory: str) -> None:
        def get_random_move(random, pkmn_data, damaging_move=False):
            if self.options.randomize_learnsets == "randomize_prefer_type":
                type1 = pkmn_data.types[0]
                type2 = None
                if len(pkmn_data.types) > 1:
                    type2 = pkmn_data.types[1]
                if type1 == "NORMAL" and (type2 == "NORMAL" or type2 is None):
                    chances = [[75, "NORMAL"]]
                elif type1 == "NORMAL" or type2 == "NORMAL":
                    if type1 == "NORMAL":
                        second_type = type2
                    else:
                        second_type = type1
                    chances = [[30, "NORMAL"], [85, second_type]]
                elif type1 == type2:
                    chances = [[60, type1], [80, "NORMAL"]]
                else:
                    chances = [[50, type1], [80, type2], [85, "NORMAL"]]
                    
                x = random.randint(0,100)
                i = 0
                n, move_type = chances[i]
                while n < x and i < len(chances):
                    i += 1
                    if i < len(chances):
                        n, move_type = chances[i]
                    else:
                        move_type = None
                
            move_pool = []
            min_power = 1 if damaging_move else 0
            if move_type is None:
                move_pool = [move_name for move_name, move_data in crystal_data.moves.items() if
                             move_data.id > 0 and not move_data.is_hm and move_name not in ["STRUGGLE", "BEAT_UP"] 
                             and move_data.power >= min_power]
            else:
                move_pool = [move_name for move_name, move_data in crystal_data.moves.items() if
                             move_data.id > 0 and not move_data.is_hm and move_data.type == move_type and move_name not in [
                                 "STRUGGLE", "BEAT_UP"] and move_data.power >= min_power]
            return random.choice(move_pool)

        def get_random_move_from_learnset(pokemon, level):
            move_pool = [move.move for move in crystal_data.pokemon[pokemon].learnset if move.level <= level]
            return self.random.choice(move_pool)

        def get_random_helditem():
            helditems = [item.item_const for item_id, item in crystal_data.items.items()
                         if "Unique" not in item.tags and "INVALID" not in item.tags]
            return self.random.choice(helditems)

        def set_rival_fight(trainer_name, trainer, new_pokemon):
            trainer.pokemon[-1][1] = new_pokemon
            self.generated_trainers[trainer_name] = trainer
        
        def find_evolution_loop(pkmn_name, evo_line):
            evo_line.add(pkmn_name)
            new_evo_line = evo_line.copy()
            pkmn_data = self.generated_pokemon[pkmn_name]
            for evolution in pkmn_data.evolutions:
                evo_name = evolution[-1]
                if evo_name in evo_line:
                    return True
                if find_evolution_loop(evo_name, new_evo_line):
                    return True
            
            return False
            
        self.generated_pokemon = copy.deepcopy(crystal_data.pokemon)
        self.generated_starters = (["CYNDAQUIL", "QUILAVA", "TYPHLOSION"],
                                   ["TOTODILE", "CROCONAW", "FERALIGATR"],
                                   ["CHIKORITA", "BAYLEEF", "MEGANIUM"])
        self.generated_trainers = copy.deepcopy(crystal_data.trainers)

        if self.options.randomize_learnsets > 0:
            for pkmn_name, pkmn_data in self.generated_pokemon.items():
                learn_levels = [1 for move in pkmn_data.learnset if move.move ==
                                "NO_MOVE" and self.options.randomize_learnsets > 1]
                for move in pkmn_data.learnset:
                    if move.move != "NO_MOVE":
                        learn_levels.append(move.level)
                
                new_learnset = [LearnsetData(level, get_random_move(self.random, pkmn_data)) for level in learn_levels]
                level_one_moveset = new_learnset[:learn_levels.count(1)]
                if self.options.ensure_damaging_move and all([crystal_data.moves[move_name].power == 0 for move_name in level_one_moveset]):
                    new_learnset[0] = get_random_move(pkmn_data, damaging_move=True)
                self.generated_pokemon[pkmn_name] = self.generated_pokemon[pkmn_name]._replace(learnset=new_learnset)
        
        #logic and levels taken from Universal pokemon randomizer
        if self.options.fix_impossible_evolutions:
            for pkmn_name, pkmn_data in self.generated_pokemon.items():
                for evolution in pkmn_data.evolutions:
                    method = evolution[0]
                    if method == 'EVOLVE_TRADE':
                        item = evolution[1]
                        if item == 'KINGS_ROCK':
                            if pkmn_name == 'POLIWHIRL':
                                evolution[0] = 'EVOLVE_LEVEL'
                                evolution[1] = 37
                            elif pkmn_name == 'SLOWPOKE':
                                evolution[0] = 'EVOLVE_ITEM'
                                evolution[1] = 'WATER_STONE'
                        elif item == 'METAL_COAT':
                            evolution[0] = 'EVOLVE_LEVEL'
                            evolution[1] = 30
                        elif item == 'DRAGON_SCALE':
                            evolution[0] = 'EVOLVE_LEVEL',
                            evolution[1] = 40
                        elif item == 'UP_GRADE':
                            evolution[0] = 'EVOLVE_LEVEL'
                            evolution[1] = 30
                        else:
                            evolution[0] = 'EVOLVE_LEVEL',
                            evolution[1] = 37
                        
                
        
        if self.options.randomize_evolutions:
            for _ in range(5):
                evolved_pokemon = list(self.generated_pokemon.keys())
                self.random.shuffle(evolved_pokemon)
                for pkmn_name, pkmn_data in self.generated_pokemon.items():
                    for evolution in pkmn_data.evolutions:
                        evolves_to = evolved_pokemon.pop()
                        if evolves_to == pkmn_name:
                            evolved_pokemon.append(evolves_to)
                            evolves_to = evolved_pokemon.pop()
                        evolution[-1] = evolves_to
                
                #loop detection
                loop = False
                for pkmn_name in self.generated_pokemon:
                    if find_evolution_loop(pkmn_name, set()):
                        loop = True
                        break
                    
                if loop:
                    continue
                else:
                    break
                        
            else:
                raise FillError(f"Failed to randomize evolutions for player {self.player}")
        
        if self.options.randomize_stats > 0:
            evolves_from = {}
            for pkmn_name, pkmn_data in self.generated_pokemon.items():
                for evolution in pkmn_data.evolutions:
                    evolves_from[evolution[-1]] = pkmn_name
            for pkmn_name, pkmn_data in self.generated_pokemon.items():
                if self.options.randomize_stats == "shuffle":
                    stats = [pkmn_data.base_stats[0], pkmn_data.base_stats[1], pkmn_data.base_stats[2], pkmn_data.base_stats[3], pkmn_data.base_stats[4]]
                    
                    if pkmn_name in evolves_from and self.options.randomize_evolutions == 0:
                        stat_shuffle_map = self.generated_pokemon[evolves_from[pkmn_name]]["stat_shuffle_map"]
                    else:
                        stat_shuffle_map = self.random.sample(range(0, 5), 5)
        
                    pkmn_data["stat_shuffle_map"] = stat_shuffle_map
                    pkmn_data.base_stats[0] = stats[stat_shuffle_map[0]]
                    pkmn_data.base_stats[1] = stats[stat_shuffle_map[1]]
                    pkmn_data.base_stats[2] = stats[stat_shuffle_map[2]]
                    pkmn_data.base_stats[3] = stats[stat_shuffle_map[3]]
                    pkmn_data.base_stats[4] = stats[stat_shuffle_map[4]]
                elif self.options.randomize_stats == "randomize":
                    first_run = True
                    while (first_run or pkmn_data.base_stats[0] > 255 or pkmn_data.base_stats[1] > 255 or pkmn_data.base_stats[2] > 255 or pkmn_data.base_stats[3] > 255
                           or pkmn_data.base_stats[4] > 255):
                        first_run = False
                        total_stats = pkmn_data.base_stats[0] + pkmn_data.base_stats[1] + pkmn_data.base_stats[2] + pkmn_data.base_stats[3] + pkmn_data.base_stats[4]
                        for i in range(5):
                            if pkmn_name in evolves_from and self.options.randomize_evolutions == 0:
                                pkmn_data.base_stats[i] = self.generated_pokemon[evolves_from[pkmn_name]].base_stats[i]
                                total_stats -= pkmn_data.base_stats[i]
                            elif i == 0: # hp
                                pkmn_data.base_stats[0] = 20
                                total_stats -= 20
                            else:
                                pkmn_data.base_stats[i] = 10
                                total_stats -= 10
                        assert total_stats >= 0, f"Error distributing stats for {pkmn_name} for player {self.player}"
                        dist = [self.random.randint(1, 101) / 100, self.random.randint(1, 101) / 100,
                                self.random.randint(1, 101) / 100, self.random.randint(1, 101) / 100,
                                self.random.randint(1, 101) / 100]
                        total_dist = sum(dist)
        
                        pkmn_data.base_stats[0] += int(round(dist[0] / total_dist * total_stats))
                        pkmn_data.base_stats[1] += int(round(dist[1] / total_dist * total_stats))
                        pkmn_data.base_stats[2] += int(round(dist[2] / total_dist * total_stats))
                        pkmn_data.base_stats[3] += int(round(dist[3] / total_dist * total_stats))
                        pkmn_data.base_stats[4] += int(round(dist[4] / total_dist * total_stats))


        if self.options.randomize_starters > 0:
            unevolved_pokemon = [ pkmn_name for pkmn_name, pkmn_data in self.generated_pokemon.items() if len(pkmn_data.evolutions) > 0 ]
            for evo_line in self.generated_starters:
                rival_fights = [(trainer_name, trainer) for trainer_name, trainer in crystal_data.trainers.items() if
                                trainer_name.startswith("RIVAL_" + evo_line[0])]

                if self.options.randomize_starters == "randomize":
                    evo_line[0] = get_random_pokemon(self.random)
                elif self.options.randomize_starters == "unevolved":
                    evo_line[0] = self.random.choice(unevolved_pokemon)
                else:
                    raise FillError(f"Unhandled option {self.options.randomize_starters} for player {self.player}")
               
                for trainer_name, trainer in rival_fights:
                    set_rival_fight(trainer_name, trainer, evo_line[0])

                rival_fights = [(trainer_name, trainer) for trainer_name, trainer in crystal_data.trainers.items() if
                                trainer_name.startswith("RIVAL_" + evo_line[1])]

                first_evolutions = self.generated_pokemon[evo_line[0]].evolutions
                evo_line[1] = self.random.choice(first_evolutions)[-1] if len(first_evolutions) else evo_line[0]
                for trainer_name, trainer in rival_fights:
                    set_rival_fight(trainer_name, trainer, evo_line[1])

                rival_fights = [(trainer_name, trainer) for trainer_name, trainer in crystal_data.trainers.items() if
                                trainer_name.startswith("RIVAL_" + evo_line[2])]

                second_evolutions = self.generated_pokemon[evo_line[1]].evolutions
                evo_line[2] = self.random.choice(second_evolutions)[-1] if len(
                    second_evolutions) else evo_line[1]
                for trainer_name, trainer in rival_fights:
                    set_rival_fight(trainer_name, trainer, evo_line[2])

                #cleans up the evolution lines showing up in the spoiler log
                if evo_line[0] == evo_line[1]:
                    evo_line.remove(evo_line[1])
                    evo_line.remove(evo_line[1])
                elif evo_line[1] == evo_line[2]:
                    evo_line.remove(evo_line[2])
                elif self.options.randomize_evolutions > 0: #there might be a pokemon with more than 3 evolution stages
                    i = 2
                    while len(self.generated_pokemon[evo_line[i]].evolutions) > 0:
                        potential_evolutions = self.generated_pokemon[evo_line[i]].evolutions
                        evo_line.append(self.random.choice(potential_evolutions)[-1])
                        i += 1

        if self.options.randomize_trainer_parties > 0:
            for trainer_name, trainer_data in self.generated_trainers.items():
                new_party = trainer_data.pokemon
                for i, pokemon in enumerate(trainer_data.pokemon):
                    new_pkmn_data = pokemon
                    if not trainer_name.startswith("RIVAL") or i != len(trainer_data.pokemon) - 1:
                        match_types = [None, None]
                        if self.options.randomize_trainer_parties == 1:
                            match_types = crystal_data.pokemon[new_pkmn_data[1]].types
                        new_pokemon = get_random_pokemon(self.random, match_types)
                        new_pkmn_data[1] = new_pokemon
                    if trainer_data.trainer_type in ["TRAINERTYPE_ITEM", "TRAINERTYPE_ITEM_MOVES"]:
                        new_pkmn_data[2] = get_random_helditem()
                    if trainer_data.trainer_type not in ["TRAINERTYPE_MOVES", "TRAINERTYPE_ITEM_MOVES"]:
                        continue
                    move_offset = 2 if trainer_data.trainer_type == "TRAINERTYPE_MOVES" else 3
                    while move_offset < len(new_pkmn_data) and new_pkmn_data[move_offset] != "NO_MOVE":
                        new_pkmn_data[move_offset] = get_random_move_from_learnset(
                            new_pkmn_data[1], int(new_pkmn_data[0]))
                        move_offset += 1
                    new_party[i] = new_pkmn_data
                self.generated_trainers[trainer_name] = self.generated_trainers[trainer_name]._replace(
                    pokemon=new_party)

        if self.options.type_themed_gyms:
            gym_trainers = [
                [ 'FALKNER_1', 'BIRD_KEEPER_2', 'BIRD_KEEPER_1' ],
                [ 'BUGSY_1', 'TWINS_1', 'TWINS_4', 'BUG_CATCHER_6', 'BUG_CATCHER_5', 'BUG_CATCHER_7' ],
                [ 'WHITNEY_1','BEAUTY_1', 'BEAUTY_2', 'LASS_1', 'LASS_2' ],
                [ 'MORTY_1', 'MEDIUM_1', 'MEDIUM_2', 'SAGE_6', 'SAGE_5' ],
                [ 'CHUCK_1', 'BLACKBELT_T_2', 'BLACKBELT_T_4', 'BLACKBELT_T_5', 'BLACKBELT_T_7' ],
                [ 'JASMINE_1' ],
                [ 'PRYCE_1', 'SKIER_1', 'SKIER_2', 'BOARDER_1', 'BOARDER_2', 'BOARDER_3' ],
                [ 'CLAIR_1', 'COOLTRAINERM_3', 'COOLTRAINERM_4', 'COOLTRAINERM_5', 'COOLTRAINERF_3', 'COOLTRAINERF_4' ],
                [ 'BROCK_1', 'CAMPER_18' ],
                [ 'MISTY_1', 'SWIMMERF_18', 'SWIMMERF_19', 'SWIMMERM_21' ],
                [ 'LT_SURGE_1', 'JUGGLER_3', 'GUITARIST_2', 'GENTLEMAN_3' ],
                [ 'ERIKA_1', 'TWINS_5', 'TWINS_6', 'PICNICKER_19', 'LASS_9', 'BEAUTY_14' ],
                [ 'JANINE_1', 'LASS_6', 'PICNICKER_5', 'CAMPER_5', 'LASS_3' ],
                [ 'SABRINA_1', 'MEDIUM_6', 'MEDIUM_7', 'PSYCHIC_T_12', 'PSYCHIC_T_2' ],
                [ 'BLAINE_1'],
                [ 'BLUE_1', ],
                [ 'WILL_1', ],
                [ 'KOGA_1', ],
                [ 'BRUNO_1' ],
                [ 'KAREN_1', ],
                [ 'CHAMPION_1' ]
            ]
            
            for gym in gym_trainers:
                poke_type = get_random_type(self.random)
                for trainer_name in gym:
                    trainer_data = self.generated_trainers[trainer_name]
                    new_party = trainer_data.pokemon
                    for i, pokemon in enumerate(trainer_data.pokemon):
                        new_pkmn_data = pokemon
                        new_pokemon = get_random_pokemon_by_type(self.random, poke_type)
                        new_pkmn_data[1] = new_pokemon
                        if trainer_data.trainer_type not in ["TRAINERTYPE_MOVES", "TRAINERTYPE_ITEM_MOVES"]:
                            continue
                        move_offset = 2 if trainer_data.trainer_type == "TRAINERTYPE_MOVES" else 3
                        for j in range(move_offset, len(new_pkmn_data)):
                            if new_pkmn_data[j] == 'NO_MOVE':
                                continue
                            new_pkmn_data[j] = get_random_move_from_learnset(
                                new_pkmn_data[1], int(new_pkmn_data[0]))
                        new_party[i] = new_pkmn_data
                    
                    self.generated_trainers[trainer_name] = self.generated_trainers[trainer_name]._replace(
                        pokemon=new_party)

        generate_output(self, output_directory)

    def fill_slot_data(self) -> Dict[str, Any]:
        slot_data = self.options.as_dict(
            "randomize_hidden_items",
            "randomize_badges",
            "randomize_starters",
            "randomize_wilds",
            "randomize_learnsets",
            "tmhm_compatibility",
            "blind_trainers",
            "better_marts",
            "goal",
            "require_itemfinder"
        )
        return slot_data

    def write_spoiler(self, spoiler_handle) -> None:
        if self.options.randomize_starters > 0:
            spoiler_handle.write(f"\n\nStarter Pokemon ({self.multiworld.player_name[self.player]}):\n\n")
            for evo_line in self.generated_starters:
                evo_string = f"{evo_line[0]}"
                i = 1
                while i < len(evo_line):
                    evo_string += f" -> {evo_line[i]}"
                    i += 1
                evo_string += "\n"
                spoiler_handle.write(evo_string)
                

    def create_item(self, name: str) -> PokemonCrystalItem:
        return self.create_item_by_code(self.item_name_to_id[name])

    def create_item_by_code(self, item_code: int) -> PokemonCrystalItem:
        return PokemonCrystalItem(
            self.item_id_to_name[item_code],
            get_item_classification(item_code),
            item_code,
            self.player
        )
