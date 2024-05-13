from Options import Toggle, Choice, DefaultOnToggle, Range, PerGameCommonOptions
from dataclasses import dataclass


class Goal(Choice):
    """Elite Four: collect 8 badges and enter the Hall of Fame
        Red: collect 16 badges and defeat Red at Mt. Silver"""
    display_name = "Goal"
    default = 0
    option_elite_four = 0
    option_red = 1


class RandomizeHiddenItems(Choice):
    """Adds hidden items to the randomization pool.
        If filler_only, then only FILLER tagged items will be added to hidden locations"""
    display_name = "Randomize Hidden Items"
    default = 0
    option_vanilla = 0
    option_randomize = 1
    option_filler_only = 2

class RandomizeBadges(Choice):
    """Shuffles badges, either separately, or with other items"""
    display_name = "Randomize Badges"
    default = 0
    option_vanilla = 0
    option_shuffle = 1
    option_randomize = 2

class RequireItemfinder(DefaultOnToggle):
    """Hidden items require Itemfinder in logic"""
    display_name = "Require Itemfinder"


class RandomizeStarters(Choice):
    """Randomizes species of starter Pokemon"""
    display_name = "Randomize Starters"
    default = 0
    option_vanilla = 0
    option_randomize = 1
    option_unevolved = 2
    


class RandomizeWilds(Toggle):
    """Randomizes species of wild Pokemon"""
    display_name = "Randomize Wilds"
    default = 0


class NormalizeEncounterRates(Toggle):
    """Normalizes chance of encountering each wild Pokemon slot"""
    display_name = "Normalize Encounter Rates"
    default = 0


class RandomizeStaticPokemon(Toggle):
    """Randomizes species of static Pokemon encounters"""
    display_name = "Randomize Static Pokemon"


class RandomizeTrainerParties(Choice):
    """Randomizes Pokemon in enemy trainer parties"""
    display_name = "Randomize Trainer Parties"
    default = 0
    option_vanilla = 0
    option_match_types = 1
    option_completely_random = 2

class TypeThemedGyms(Toggle):
    """All pokemon in a gym/elite 4/champion will be of the same (random) type"""
    display_name = "Type Themed Gyms"
    default = 0

class RandomizeLearnsets(Choice):
    """start_with_four_moves: Random movesets with 4 starting moves
    randomize: Random movesets
    vanilla: Vanilla movesets"""
    display_name = "Randomize Learnsets"
    default = 0
    option_vanilla = 0
    option_randomize = 1
    option_start_with_four_moves = 2
    option_randomize_prefer_type = 3

class EnsureDamagingMove(Toggle):
    """Ensures each pokémon starts with a damaging move.
    Does nothing if randomize_learnsets is vanilla"""
    display_name = "Ensure Damaging Move"

class RandomizeStats(Choice):
    """shuffle: shuffle each Pokémon's stats
    randomize: randomize each Pokémon's stats, keeping the same base stat total"""
    display_name = "Randomize Stats"
    default = 0
    option_vanilla = 0
    option_shuffle = 1
    option_randomize = 2

class RandomizeEvolutions(Toggle):
    """Each Pokemon will evolve in the same manner (e.g. level up, evolution stone, etc.), 
        but into a different random Pokemon"""
    default = 0

class TmHmCompatibility(Choice):
    """Which Pokemon can learn which TM/HM"""
    display_name = "TM/HM Compatibility"
    default = 0
    option_vanilla = 0
    option_randomize = 1
    option_full = 2


class ReusableTMs(Toggle):
    """TMs can be used an infinite number of times"""
    display_name = "Reusable TMs"
    default = 0


class GuaranteedCatch(Toggle):
    """Balls have a 100% success rate"""
    display_name = "Guaranteed Catch"
    default = 0


class MinimumCatchRate(Range):
    """Sets a minimum catch rate for wild Pokemon"""
    display_name = "Minimum Catch Rate"
    default = 0
    range_start = 0
    range_end = 255


class BlindTrainers(Toggle):
    """Trainers have no vision and will not start battles unless interacted with"""
    display_name = "Blind Trainers"
    default = 0


class BetterMarts(Toggle):
    """Improves the selection of items at Pokemarts"""
    display_name = "Better Marts"
    default = 0


class ExpModifier(Range):
    """Scale the amount of Experience Points given in battle.
    Default is 20, for double set to 40, for half set to 10, etc.
    Must be between 1 and 255"""
    display_name = "Experience Modifier"
    default = 20
    range_start = 1
    range_end = 255
    
class FixImpossibleEvolutions(Toggle):
    """Replaces impossible evolutions (trades) with possible ones (evolution stones or level up)"""
    display_name = "Fix Impossible Evolutions"
    default = 0

class ItemReceiveSound(DefaultOnToggle):
    """Play item received sound on receiving a remote item"""
    display_name = "Item Receive Sound"

class FastEggHatching(Toggle):
    """Reduces the time to hatch eggs to one egg cycle (256 steps)"""
    display_name = "Fast Egg Hatching"
    default = 0

@dataclass
class PokemonCrystalOptions(PerGameCommonOptions):
    goal: Goal
    randomize_badges: RandomizeBadges
    randomize_hidden_items: RandomizeHiddenItems
    require_itemfinder: RequireItemfinder
    randomize_starters: RandomizeStarters
    randomize_wilds: RandomizeWilds
    normalize_encounter_rates: NormalizeEncounterRates
    randomize_static_pokemon: RandomizeStaticPokemon
    randomize_trainer_parties: RandomizeTrainerParties
    type_themed_gyms: TypeThemedGyms
    randomize_learnsets: RandomizeLearnsets
    ensure_damaging_move: EnsureDamagingMove
    randomize_stats: RandomizeStats
    randomize_evolutions: RandomizeEvolutions
    tmhm_compatibility: TmHmCompatibility
    reusable_tms: ReusableTMs
    guaranteed_catch: GuaranteedCatch
    minimum_catch_rate: MinimumCatchRate
    blind_trainers: BlindTrainers
    better_marts: BetterMarts
    experience_modifier: ExpModifier
    fix_impossible_evolutions: FixImpossibleEvolutions
    item_receive_sound: ItemReceiveSound
    fast_egg_hatching: FastEggHatching
