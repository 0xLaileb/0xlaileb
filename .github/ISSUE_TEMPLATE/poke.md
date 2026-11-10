---
name: Poke a byte
about: Write one byte into the shared memory on the profile
title: "poke 00 E0"
---

Only the title matters: `poke <addr> <value>`, two hex bytes. The address is the cell (00..FF, row by row), the value is an RGB332 colour (E0 red, 1C green, 03 blue, FF white, 00 erase). A workflow closes this issue and redraws the card.