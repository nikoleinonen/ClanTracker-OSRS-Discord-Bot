# ClanTracker OSRS Discord Bot

[![Discord](https://img.shields.io/discord/1360328606257119463?label=Discord&logo=discord&logoColor=white)](https://discord.gg/y4tmVW9p)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

This Discord bot acts as a crucial bridge between your Discord server and **ClanTracker OSRS** desktop application. It automatically sets up dedicated channels in your server, generates a unique identifier for your clan, and serves configuration and manual data points to the application via API endpoint.

**Core Purpose:** To allow clan leaders to manage and create clan specific settings, create rank system and set manual player data that cannot be tracked via API endpoints directly within Discord, which the ClanTracker OSRS application can then fetch and use.

---

# Features

### **Automatic Server Setup** 

>Creates a dedicated category (**`ClanTracker`**) and necessary text channels (**`ct-info`**, **`ct-config`**, **`ct-manual-points`**, **`ct-commands`**) when added to a server.

### **Unique Clan Identifier** 

> Generates a unique **`clan_identifier`** for each Discord server it joins. This identifier is used by the **ClanTracker OSRS** application to fetch the correct data.

### **ClanTracker OSRS Application Configuration (`ct-config`)** 

>Allows clan leaders to define clan-specific settings (like TempleOSRS group ID, theme colors, rank thresholds, custom point calculations) in an INI-like format within the **`ct-config`** channel.

### **Manual Data Entry (`ct-manual-points`)** 

>Provides a channel (**`ct-manual-points`**) for entering player-specific boolean flags or other data points used for custom calculations within the ClanTracker OSRS application.

> [!CAUTION]
> The API fetches data from the **`ct-config`** and **`ct-manual-points`** text channels.
> **Do not** post any sensitive information in these channels — anything you share may be parsed into the application and become visible to others!

---

# Base Setup **`ct-config`**

> [!NOTE]
> Copy everything from below one by one, including the backticks and ini — this keeps the formatting neat when pasting!

<pre>
```ini
[templeosrs_group_id]
group_id = 
```
</pre>

<pre>
```ini
[theme]
background_color_custom = #0E0E0E
menu_color_custom = #151515
accent_color_custom = #124080
selected_color_custom = #0d3265
txt_color_custom = #D2D2D2
```
</pre>

<pre>
```ini
[ranks]
rank_thresholds = 0, 5, 10, 20, 40, 60, 80, 120, 160, 180, 200
rank_titles = Burger, Rank 1, Rank 2, Rank 3, Rank 4, Rank 5, Rank 6, Rank 7, Rank 8, Rank 9, Rank 10
num_ranks = 11
```
</pre>

<pre>
```ini
[gilded_ehc]
use_gilded_ehc = true
```
</pre>

<pre>
```ini
[raid_keys]
burger_raids = chambers of xeric, tombs of amascut, theatre of blood
regular_raids = chambers of xeric, theatre of blood, tombs of amascut expert
cm_raids = chambers of xeric challenge mode, theatre of blood challenge mode
all_raids = chambers of xeric, chambers of xeric challenge mode, theatre of blood, theatre of blood challenge mode, tombs of amascut, tombs of amascut expert
```
</pre>

<pre>
```ini
[custom_base_keys]
wild_main_bosses_base_kc = bosses.callisto, bosses.vetion, bosses.venenatis
```
</pre>

<pre>
```ini
[custom_total_keys]
wild_main_bosses_total_kc = bosses.callisto, bosses.vetion, bosses.venenatis
```
</pre>

<pre>
```ini
[custom_clog_keys]
infernal_fire_quiver = 21295, 6570, 28947
```
</pre>

<pre>
```ini
[records]
6h = true
day = false
72h = false
week = false
month = false
year = false
```
</pre>

<pre>
```ini
[points_Manual Points]
example_rule = 1 ; type=boolean ; data=points.manual_points
```
</pre>

<pre>
```ini
[points_Example Category 1]
infernal_cape | Infernal Cape = 5 ; type=boolean ; data=items ; value=21295
1000_bandos | 1000 Bandos KC = 2 ; type=threshold ; data=bosses.general graardor ; value=1000
per_250_raids | Per 250 Raids Completed = 1 ; type=per_value ; data=total_raid_kc ; value=250
```
</pre>

---

# Point System
This system lets you fully customize how points are awarded to players based on achievements, kill counts, stats, items, and more. You define the rules in the **`ct-config`** channel, and the system automatically calculates each player’s points by cross-referencing their data.

## Formatting points in **`ct-config`** channel

Follow this formula for each group of points you create:

```ini
[points_Category]
rule_name | Display Name = points ; type= ; data= ; value=
```

- **`points_Category`** = **MUST** contain points_ prefix
- **`rule_name`** = Unique identifier for the rule.
- **`Display Name`** = How it is displayed in the application.
- **`points`** = How many points this rule grants, if eligible.
- **`type`** = 
  - `boolean`: Yes/No check (does the player have this?).
  - `threshold`: Award points if a value meets or exceeds a threshold.
  - `per_value`: Award points repeatedly based on how many times the value fits into the player's stat.
- **`data`** = Check Data Sources section for more information.
- **`value`** = The numeric value to compare against (only for `threshold` or `per_value` types).

---

### Example Rules

#### **Simple Boolean Check**
>Award 5 points if the player has Infernal Cape (item ID `21295`):
>```ini
>infernal_cape | Infernal Cape = 5 ; type=boolean ; data=items ; value=21295
>```

>Award 10 points if the player has max cape:
>```ini
>max_cape | Max cape = 10 ; type=boolean ; data=max cape
>```

#### **Threshold Check**
>Award 3 points if the player’s base level is at least 90:
>```ini
>base_90 | Base Level 90 = 3 ; type=threshold ; data=base level ; value=90
>```

>Award 5 points if the player’s bandos kc is at least 1000:
>```ini
>1000_bandos | 1000 Bandos KC = 5 ; type=threshold ; data=bosses.general graardor ; value=1000
>```

#### **Per Value Check**
>Award 1 point for every 250 raids completed:
>```ini
>per_250_raids | Per 250 Raids Completed = 1 ; type=per_value ; data=total_raid_kc ; value=250
>```

>Award 5 points for every 100 clogs the player has:
>```ini
>per_100_clogs | Per 100 Clogs = 5 ; type=per_value ; data=clog.collections ; value=100
>```

---

# Data Sources

### Collection log item IDs
[**TempleOSRS API**](https://templeosrs.com/api/collection-log/items.php)

---

### Adding custom data sources

Adding custom data sources gives you more flexibility to create a more robust point system.

To reference these values in your point calculations, use the **`custom.`** prefix before the custom **`rule_name`** you created.

>Example: Creating custom keys for Wilderness bosses and retrieving the base kill count from the selected bosses.
>
>These will be nested under **`custom`**.
>```ini
>[custom_base_keys]
>wild_main_bosses_base = bosses.callisto, bosses.vetion, bosses.venenatis
>wild_demi_bosses_base = bosses.artio, bosses.spindel, bosses.calvarion
>```

>Example: Adding multiple unrelated values together as an example of how flexible this is.
>
>This will create a new key called **`custom_random_example`**, which will be nested under **`custom`**.
>```ini
>[custom_total_keys]
>custom_random_example = bosses.chambers of xeric, clues.clue_all, misc.soul wars zeal
>```

>Example: Creating **`toa_transmogs`** key which will be nested under **`custom`**.
>
>Returns **`true`** or **`false`** depending on whether all items were found.
>```ini
>[custom_clog_keys]
>toa_transmogs = 27377, 27378, 27379, 27380, 27381
>```

---

### Rewarding points from custom data sources

Now that we have set our custom keys, we can use them to grant points.

>Example: Giving points for wilderness bosses.
>
>In this example, if the player has base KC of 50 for specified bosses, then they get 2 and 1 points.
>```ini
>[points_Wilderness Bosses]
>wilderness_boss_base = Wilderness Boss Base KC = 2 ; type=threshold ; data=custom.wild_main_bosses_base ; value=50
>wilderness_demi_boss_base = Wilderness Demi Boss Base KC = 1 ; type=threshold ; data=custom.wild_wild_demi_bosses_base ; value=50
>```

>Example: Giving points for custom total KC or completions, which ever you specified.
>
>In this example, if the player has combined of 5000 of bosses.chambers of xeric, clues.clue_all, misc.soul wars zeal KC, then they get 5 points.
>```ini
>[points_Total KC]
>custom_random = Messed up = 5 ; type=threshold ; data=custom.custom_random_example ; value=5000
>```

>Example: Giving 3 points for having all ToA transmogs.
>```ini
>[points_Transmogs]
>all_toa_transmogs = All ToA Transmogs = 3 ; type=boolean ; data=custom.toa_transmogs
>```

---

### Default data sources list

The **`data`** field in each rule in point configuration must match a key in **`member_data.json`** (found in application data folder). Below is a list of data sources you can use:

### **General**  
- `player` - $\textsf{\color{#fd00d1}{string}}$
- `country` - $\textsf{\color{#fd00d1}{string}}$
- `game_mode` - $\textsf{\color{#fd00d1}{string}}$
- `ehp` - $\textsf{\color{#4ec9b0}{integer}}$
- `ehb` - $\textsf{\color{#4ec9b0}{integer}}$
- `ehpb` - $\textsf{\color{#4ec9b0}{integer}}$
- `overall` - $\textsf{\color{#4ec9b0}{integer}}$
- `overall level` - $\textsf{\color{#4ec9b0}{integer}}$
- `base level` - $\textsf{\color{#4ec9b0}{integer}}$
- `200m skill` - $\textsf{\color{#4ec9b0}{integer}}$
- `base xp` - $\textsf{\color{#4ec9b0}{integer}}$
- `max cape` - $\textsf{\color{#940000}{boolean}}$
- `skill cape` - $\textsf{\color{#940000}{boolean}}$


### **Skills**  
#### **Combat Skills**  
- `skills.combat skills.attack` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.attack_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.defence` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.defence_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.strength` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.strength_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.hitpoints` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.hitpoints_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.ranged` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.ranged_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.prayer` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.prayer_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.magic` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.magic_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.combat skills.combat xp` - $\textsf{\color{#4ec9b0}{integer}}$  


#### **Gathering Skills**  
- `skills.gathering skills.woodcutting` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.woodcutting_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.fishing` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.fishing_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.mining` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.mining_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.farming` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.farming_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.hunter` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.hunter_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.gathering skills.gathering xp` - $\textsf{\color{#4ec9b0}{integer}}$  


#### **Production Skills**  
- `skills.production skills.cooking` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.cooking_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.fletching` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.fletching_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.crafting` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.crafting_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.smithing` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.smithing_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.herblore` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.herblore_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.runecraft` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.runecraft_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.production skills.production xp` - $\textsf{\color{#4ec9b0}{integer}}$ 


#### **Utility Skills**  
- `skills.utility skills.firemaking` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.firemaking_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.agility` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.agility_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.thieving` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.thieving_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.slayer` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.slayer_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.construction` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.construction_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.sailing` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.sailing_level` - $\textsf{\color{#4ec9b0}{integer}}$  
- `skills.utility skills.utility xp` - $\textsf{\color{#4ec9b0}{integer}}$ 


### **Bosses**  
- `bosses.abyssal sire` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.alchemical hydra` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.barrows chests` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.bryophyta` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.callisto` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.cerberus` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.chambers of xeric` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.chambers of xeric challenge mode` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.chaos elemental` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.chaos fanatic` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.commander zilyana` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.corporeal beast` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.crazy archaeologist` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.dagannoth prime` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.dagannoth rex` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.dagannoth supreme` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.deranged archaeologist` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.general graardor` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.giant mole` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.grotesque guardians` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.hespori` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.kalphite queen` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.king black dragon` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.kraken` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.kreearra` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.kril tsutsaroth` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.mimic` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.obor` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.sarachnis` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.scorpia` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.skotizo` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.the gauntlet` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.the corrupted gauntlet` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.theatre of blood` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.thermonuclear smoke devil` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.tzkal-zuk` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.tztok-jad` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.venenatis` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.vetion` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.vorkath` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.wintertodt` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.zalcano` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.zulrah` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.the nightmare` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.tempoross` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.theatre of blood challenge mode` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.phosanis nightmare` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.nex` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.rift` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.tombs of amascut` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.tombs of amascut expert` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.phantom muspah` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.artio` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.calvarion` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.spindel` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.duke sucellus` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.the leviathan` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.the whisperer` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.vardorvis` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.scurrius` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.lunar chests` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.sol heredit` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.araxxor` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.hueycoatl` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.amoxliatl` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.the royal titans` - $\textsf{\color{#4ec9b0}{integer}}$
- `bosses.total kc` - $\textsf{\color{#4ec9b0}{integer}}$


### **Raids**  
- `raids.base_burger_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `raids.total_burger_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `raids.base_regular_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `raids.total_regular_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `raids.base_cm_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `raids.total_cm_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `raids.base_all_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `raids.total_all_raid_kc` - $\textsf{\color{#4ec9b0}{integer}}$


### **Miscellaneous**  
- `misc.lms` - $\textsf{\color{#4ec9b0}{integer}}$  
- `misc.soul wars zeal` - $\textsf{\color{#4ec9b0}{integer}}$
- `misc.bounty hunter hunter` - $\textsf{\color{#4ec9b0}{integer}}$  
- `misc.bounty hunter rogue` - $\textsf{\color{#4ec9b0}{integer}}$  
- `misc.pvp arena` - $\textsf{\color{#4ec9b0}{integer}}$  
- `misc.colosseum glory` - $\textsf{\color{#4ec9b0}{integer}}$  


### **Clues**  
- `clues.clue_all` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clues.clue_beginner` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clues.clue_easy` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clues.clue_medium` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clues.clue_hard` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clues.clue_elite` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clues.clue_master` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clues.clue_grandmaster` - $\textsf{\color{#4ec9b0}{integer}}$  


### **Custom** 
- [custom_base_keys]
 - `custom.your custom rule name` - $\textsf{\color{#4ec9b0}{integer}}$  
- [custom_total_keys]
 - `custom.your custom rule name` - $\textsf{\color{#4ec9b0}{integer}}$  
- [custom_clog_keys]
 - `custom.your custom rule name` - $\textsf{\color{#940000}{boolean}}$


### **Points**  
- `points.total points` - $\textsf{\color{#4ec9b0}{integer}}$ 
- `points.rank` - $\textsf{\color{#fd00d1}{string}}$


### **Collection Log**  
- `clog.collections` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clog.ehc` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clog.collection_categories` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clog.pets` - $\textsf{\color{#4ec9b0}{integer}}$  
- `clog.all_pets` - $\textsf{\color{#940000}{boolean}}$
- `clog.items` - $\textsf{\color{#4ec9b0}{integer}}$  

---

# Contributing

We welcome contributions to help enhance and expand the application! Whether you have ideas for new features, bug fixes, or general improvements, feel free to fork the repository, submit an issue, or open a pull request. Your contributions are highly appreciated.

*Disclaimer: I apologize for any questionable code quality you might encounter — the project was largely built with the helping hand of Gemini Code Assistant. :D*

Additionally, you can join the ClanTracker Discord to share feedback, report bugs, or ask questions!

[**ClanTracker Discord**](https://discord.gg/y4tmVW9p)

---

# License

#### TODO