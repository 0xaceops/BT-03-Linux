"""Danh muc chu de bach khoa. Moi AI worker nhan 1-2 danh muc (bien CATEGORIES)."""
COLORS = ["red", "blue", "green", "yellow", "black", "white", "brown", "orange", "purple", "pink", "grey", "golden"]
NOUNS = {
 "animals": "dog cat horse cow pig sheep goat rabbit fox wolf bear lion tiger elephant giraffe zebra monkey owl eagle parrot penguin duck swan frog turtle snake fish shark whale dolphin octopus crab butterfly bee spider deer squirrel camel kangaroo panda hedgehog".split(),
 "plants": "tree flower rose tulip sunflower daisy cactus fern mushroom leaf grass bamboo palm oak pine maple lotus orchid lily ivy moss seed acorn clover".split(),
 "food": "apple banana orange lemon cherry grape strawberry pear peach carrot tomato potato corn bread cheese egg cake pizza burger cookie teacup coffee-cup pumpkin onion pepper".split(),
 "tools": "hammer saw wrench screwdriver axe shovel scissors knife needle ladder bucket rope anchor key lock bell lamp candle clock compass telescope microscope magnet".split(),
 "vehicles": "car bus truck bicycle motorcycle train boat ship sailboat airplane helicopter rocket balloon tractor submarine canoe cart sled".split(),
 "buildings": "house castle tower bridge lighthouse windmill barn church temple pyramid tent igloo hut farm gate fountain statue".split(),
 "space": "sun moon star planet comet rocket satellite telescope galaxy meteor crater astronaut saturn earth mars".split(),
 "science": "atom molecule magnet battery flask prism gear lightbulb microscope skeleton skull heart brain tooth eye bone volcano crystal".split(),
 "clothing": "hat shirt dress coat boot shoe sock glove scarf crown helmet umbrella bag ring necklace glasses cap belt".split(),
}
