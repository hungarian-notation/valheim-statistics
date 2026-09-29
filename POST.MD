Theres been some confusion about the 1.0 drop rates, especially for bear trophies.

I did a deep dive into the decompilation of the `CharacterDrop.GenerateDropList` method that handles drop chances in the comments of another thread, but I thought I'd expand on it a bit with some more concrete data. The bug might not be what you think.

## Background

In the [1.0 patch notes](https://www.valheimgame.com/news/valheim-1-0-has-arrived-/), there's a little detail about drop rates:

> Tweaked how rare enemy drops work, to avoid killing a lot of enemies without ever receiving the drop

While this implies some sort of pity system to boost drop chances during dry spells, it's instead a pretty noticable nerf to already rare drop rates, especially for mobs that you don't enounter frequently, with the caveat that killing a certain number of the mob consecutively should guarentee you a drop.

## Original Algorithm:

The standard drop chance algorithm is quite simple. The game generates a random floating point number between zero and one, and then drops an item if the random number is less than the drop chance.

The chance of an item dropping is independent of the results of any past drop checks.

## Pseudo Drop Algorithm:

The new Pseudo Drop algorithm is used for rarer drops.

The game has a table called `pseudoCounter`. This table is not saved, so it starts out empty whenever the game or server process starts.

When a drop with a chance of 30% or lower is being rolled, the game performs the following procedure:

- Check if `pseudoCounter` has an existing counter for this item:
    - If it does, reduce that counter by 1
    - Otherwise, create a counter for this item from a uniformly distributed random integer between `0` inclusive and `floor(2/chance)` exclusive.
        - *For 10%, this means the counter ranges from 0 to 19*
        - *For 5%, its 0 to 39*
- Check if the `pseudoCounter` entry for this item is now less than or equal to zero.
    - If it is:
        - Reset the counter to a new integer between `0` inclusive and `floor(2/chance) + 1` exclusive.
        - Drop the item.

I've simplified a few implementation details, but nothing that changes the actual math for something like a bear trophy.

This new algorithm completely replaces the normal drop chance calculation for rare drops.

For the C# literate, [here's the decompilation](https://pastebin.com/mKg1iBcn). This algorithm spans lines 30 through 57.

## What are the odds?

First, some quirks:

- The first kill after a game/server restart actually has half the nominal drop chance.
    - A bear trophy has a 10% nominal drop chance, so the actual drop chance on first kill is 5%.
- For sustained farming (without ever restarting the server) the odds end up being a bit worse than nominal.
    - The actual drop rate of bear trophies after 100 consecutive kills is around 9.6%.
- The first kill after a successful drop actually has better (but still worse than nominal) odds than a fresh start, with odds of `2/(floor(2/chance)+1)`.
    - For a nominal 10% chance, this gives `2 / 21` or roughly 9.52%

The more important consequences of this algorithm are:

- Grinding for a single drop of a rate item will take longer on average, even if you do it without restarts.
- Restarts during farming can significantly reduce your observed drop rate.
    - In the case of 100 consecutive bear kills, **a restart every 10 kills reduces the actual drop rate to 6.5%**. That's a 35% nerf from the pre-1.0 algorithm.

## Bear Trophies

The part of this that interests me the most is how long it takes people to get their first bear trophy. 

To be clear, the bear trophy doesn't have any special logic here; all 10% drop chance items behave the same way. I think it's only more noticeably with the bears because the bears are rarer mobs and the trophy is used in several new crafting recipes that we all want to use.

I worked up a little simulation. Here's the results!

This plot shows how likely you are to get your first trophy on or before a certain kill, with the different traces corresponding to different numbers of kill per restart:

[Plot: First Drop Probability](https://i.imgur.com/itVW1pR.png)


The fewer kills you get between restarts, the more total kills you will need on average to get that trophy. If you power through and kill 16 bears in a single session without getting a trophy you are treated with better than expected odds for the next four kills, but otherwise your chances are always worse than the pre-1.0 formula.

The drop rates over longer periods are arguably even more grim, as it becomes obvious how much of a nerf this change is.

[Plot: Average Drop Rate](https://i.imgur.com/IfM3O8c.png)

Note that while the new algorithm does have an increased likelyhood of a drop after 17 consecutive kills, that's assuming you actually went 17 kills without a drop. The average **total** drops after 17 kills is still higher with the old algorithm.

## Where is the bug?

You might consider the fact that the counters reset on server load a bug, but that's more of a known limitation. As you'll see, fixing the *actual* bug renders this irrelevant.

I've seen people pointing out that there is technically an off by one error in the random intervals. This is true, but it makes almost no difference. At 200 bear kills, this  accounts for a variance of around half a trophy.

No, the **actual** bug is that the pseudo-drop algorithm falls afoul of something like the inspection paradox. It generates its first counter interval as if it had just dropped an item, when it should instead be choosing a starting interval as if we were joining an existing sequence of drops at a random point.

In other words, the current algorithm is equivalent to assuming the first interval is **always** the maximum length, and then choosing a random point in that interval as the starting counter. The proper method would be to choose from all possible points in all possible initial intervals. This is a triangular distribution that favors smaller counter values.

Here are the plots you'd get if the devs implemented this fix:

[Plot: First Drop Probability (Fixed)](https://i.imgur.com/G0K0Gs4.png)
[Plot: Average Drop Rate (Fixed)](https://imgur.com/9BHimNs)

Bingo! We've reduced the chance of (and put an upper bound on) dry spells, but now the worst case scenario (restarting after every kill) is identical in behavior to the pre-1.0 odds, and we've done all this without changing the overall drop rate in the long term.

## In the meantime...

If there's significant interest, I can investigate implementing this fix as a mod. It shouldn't be too crazy, but I guess this would have to touch the server side and I don't have a ton of experience with Valheim modding specifically. Preferably, someone with an established modding workflow and interest in this problem would implement this adjusted algorithm. More preferably, the devs would quickly patch this; it's not much work at all.

I haven't seen this documented, but there is actually a global key you can set to disable the new algorithm. Simply run the following console commands:

    devcommands 
    setkey NoPseudoDrops

This will, of course, mark your world/character as cheated, and this command is unavailable on dedicated servers without certain mods.