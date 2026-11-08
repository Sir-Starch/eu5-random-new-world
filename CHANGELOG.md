# Changelog

## Unreleased

- Keep **Total Chaos** in the automatic name of an untouched random draw; manual changes
  name it **Custom world**. The code keeps that origin when shared or reopened. Add
  **Randomize settings again** to Total Chaos in both windows, keeping the seed.

- Keep world switching responsive: prepare maps on a cancellable background worker, discard
  obsolete requests and reuse the four most recently viewed maps. Updating the window no
  longer reloads every revealed atlas just to decide whether comparison is available.

- Allow substantial enclosed inland seas, with their own coastal areas and no ocean currents.
  Small enclosed waters become lakes before ports and terrain are built, including pockets
  cut off when straits are narrowed. Such a pocket previously stopped world generation with
  "generated sea zones cannot reach the Old World seas". Ocean routes still have to connect.

- Keep the open country/place card, map position and highlight while background generation
  updates its progress; reload the map only when its world or language changes.

- Show each completed world in the library as soon as it is ready, while the remaining
  queued worlds continue generating.

- Start every country of the New World with its laws in place. A generated state took a template
  made for a lower level of technology, so royal court customs, feudal law and cultural
  traditions, and nearly every law of a sacred centre's theocracy, opened with *No Policy
  enacted* and cost political power and months to fix. Each law a state sees at the start now
  holds a policy that the base game's countries of the same government hold, the one that leans
  the way the country's own societal values already lean. A law the game would not grant at the
  start is left out: feudal law and the republican foundation wait for the institution of
  legalism, and royal court customs for the third level of technology, as in the base game.

- Keep each country's alliances and guarantees within what it can carry. Leagues of the New
  World gave small countries up to five alliances and four guarantees; the game charges each
  treaty diplomatic capacity by the partner's size, so nine countries started over a limit even a
  ruler of the highest diplomacy could not lift, with lower prestige, subject loyalty and cabinet
  efficiency. A country now starts with the treaties it trusts most, as many as two alliances
  between equals cost; the others stay part of its history.

- Tell each country's past as a story. *Our History* read like a list of dated records
  ("1192: Society Unichita could no longer hold society Kiosaghe, which broke away. Recorded
  place: Oletan."). It now tells how the country began, what befell it (lands that broke away
  one after another make one sentence, so do the wars of two neighbours) and where it stands
  today: its overlord, vassals, allies, protectors and rivals. The generator's window tells the
  same story above the chronicle's events, in every language.

- Show names instead of keys in the game. The *Our History* decision, the events of the
  recorded past in a country's list of events, the names of the four fantasy formables and the
  lands of the formables in their tooltips showed their localization keys. The export now
  refuses a world that asks the game for a text it does not write.

- Show societal values as the game does. The generator's window lists all eleven values the
  game shows at the start, in the game's order and with the values a country inherits from its
  template, each with its two poles, the one it leans to lit and how far it leans.

- Move the choice to show the New World before you play to the **World** tab, beside the
  other options of the world, and name it for what it does: **Terra Incognita in the lobby**.
  The box is on by default (the New World is covered on the country-selection map and in the
  world's pictures); clearing it shows them. It had read the other way round, as *Show the
  New World before you play it* on **Save and play**, with the same default (covered). The
  choice itself is unchanged: it is a preference of the generator, each world keeps its own
  setting, and a finished world's page changes it without generating again.

- Let regional powers use their administrative capacity and expand coherently in the new
  region layout. Regional ambitions now check that their centre has room to grow; a realm's
  coordination follows the share of its capacity in use, and overload adds division pressure.
  Independence needs a new defeat before old fear can make the country submit again.

- Make continents faster. *Choose a continent* draws its six sketches side by side instead of
  one after another, and keeps them: the world made from a chosen sketch starts from its land
  instead of drawing it again. The area of the game's map that a New World replaces is chosen
  once per game version and kept. On the reference machine six sketches took 36 seconds, or
  22 once the area is kept, where they took three and a half minutes; a world takes under four
  minutes where it took five, and less when it is made from a sketch. Terrain, mountains and
  vegetation no longer wait for the rest of the generator, and the game's scripts are read once
  for all the checks. Every world is the same, byte for byte. The cache of made land no longer
  grows without bound: it keeps the last four continents and the last sketches (it had reached
  13 GB). The history of the New World's peoples is made in 22 seconds instead of 36, with the
  same result: on the reference machine a world now takes about three and a half minutes.

- Name the New World's regions after their peoples, and show the game's names in the
  generator. A region takes its name in the language most of its land speaks, as areas and
  provinces already did, and the colonies and realms named after it follow. The generator's
  map labelled regions and empty areas by the base game's names (Alaska, Canada), which the
  game never showed. It now writes what the game writes, and a place's card adds which base
  game region's events, advances and AI goals apply there (*Counts as Alaska in the game's
  rules*).

- Lay out the New World's regions as the Americas lie. North and South America are now
  bands from north to south, so an archipelago no longer puts the Andes and Colombia north of
  Canada. Each region takes the place its namesake has in its continent: Alaska in the
  north-west, the West Coast in the west, Central America in the south. Where the land
  allows, the land decides between neighbouring places. A region used to go wherever its
  land was most alike, even across the continent: Central America beside Alaska, the West
  Coast on the east shore, Colombia on an island in the east. The regions' land also matches
  better: Central America's climate on the reference world was almost entirely unlike
  vanilla's and is now close to it.

- Let every land country of the New World settle the frontier. The game grants the *Settle
  the Frontier* action only to countries whose original capital lies in some American
  regions, and a generated world kept that list, so about half of its countries could not
  expand into the empty land beside them. The world now grants it across the whole New World;
  the Old World and Oceania keep the game's own rule.

- Put historical opinions on the game's scale. Each remembered cause now takes the value and
  yearly decay of the game's own opinion of its kind (*Good relations* +50, *Recent Conflict
  Lost* −40, *Border Aggression* −25 and others) in proportion to how much of the memory
  survives to 1337. They were a few points before, and faded within a few years.

- Show on the generator's Relations tab what the game shows: each country's opinion of others on
  the first day, line by line under the game's names, the opinions of its alliances, rivalries,
  subjects and guarantees included, with each line's value, its yearly fade and their sum. The
  historical opinions are now called *Goodwill* and *Contention* where they were *Trust* and
  *Rivalry*, which the game uses for its own trust and rivals.

- Show each location's start development as the game computes it, on the Development lens and
  the location's card, instead of the generator's own society complexity. Rivers now count into
  development by the game's river sizes (checked against a saved game), which raises the start
  development of river land by 0.5 to 1. A world made before this says its development is not
  recorded.

- Keep the generator's own scales out of the country card. The Society tab shows the government
  and country rank under the game's names and the societal values, without the technology level
  and the model's eight trait meters, which the game does not show. The Place tab shows whether
  the *Extraordinary peoples* set for the world took shape, not the generator's ordinary
  regional aims.

- Name places in the window as the game does in the chosen language: a generated location's or
  area's name is transliterated as the world's own texts write it (*Куштакечери*, not
  *Cuxtaquecheri*), and a country without a written rank shows the game's *County*.

- Give the formable countries real goals. Any country that holds enough of a territory, its
  capital inside, may form a union, confederation, league or realm, not only the states of
  1337; a commonwealth also opens to its people's culture group. The realm becomes the realm
  of a whole generated region: 40% of it and its greatest city, one for every region with
  several states and for every region holding a lower formable's seat. Unions and
  commonwealths grow to 60 places. A fantasy empire of the continent (level 5, shown when the
  game rules allow fantasy formables) asks for half of it, hegemony and the empire rank. A
  formation gives cores on the rest of its territory, so the game's own *Claims on Province*
  opens against every holder, and opens a government reform of its family (*Council of the
  Valleys*, *Law of One People*, *Provinces of the Realm* and others). The colonial federation becomes a nation of independent
  settlers or of the leader of a colonial federation, named after its region and renamed on
  founding in its founders' tradition (*United Provinces*, *United Captaincies*, *United
  Colonies*, *Free State* or *Generality of X*).

- Offer each formable as a mission, *Road to X*: hold its seat, gather half the land it asks
  for, then proclaim it.

- Add goals beyond the ladder: an Empire of the Two Shores for a native power that reaches
  the Old World, a Crown of Two Worlds for a European court that moves to the New World, an
  Empire of the Two Oceans for a holder of ports on both oceans (the two shores and two oceans
  shown with fantasy formables), a Great League for the leader of a confederation and a
  Realm of Two Peoples for a state of settlers and natives together.

- Let the founder of a formable choose its name: the one it was proclaimed under, or the
  name of the land it rules (its seat's region, or a realm's greatest city).

- Restore the realms the history divided. A realm or union that broke apart before 1337 and
  has two living heirs becomes a formable restoration of its old land, named as the
  chronicle names it (*Restored X*), offered to its heirs only; when one restores it, each
  other heir must recognize the restored crown or deny it and become its rival.

- Let the AI pursue the formables. A country that could form a union, commonwealth,
  realm, nation or restoration weighs wars on the holders of its territory higher (from the
  second age; realms from the age of discovery).

- Adapt four of the game's American chains to generated worlds: the decline of a fallen
  realm's old seat (from Cahokia), the Grand Council of a confederation (from the
  Haudenosaunee), the balance of an alliance of three (from the Triple Alliance) and the
  assembly that decides how a new nation is governed (from the United States), with the
  original chains' modifiers copied under the new stories' names.

- Bring the recorded past back as events: a country may remember the land it lost, an old
  pact, kin who settled across the border, a shrine it visits under another's peace, or, as
  an heir, the realm its people once shared, and choose what to do about it (a core on the
  lost land or the shrine, renewed friendship, or letting it rest). Each event names its cause
  in the history.

- Add the world setting **Reveal the New World at the start**, for multiplayer, off by
  default and saved in world codes. Switched on, the world writes one on_action file that
  has the country of every human player discover every area of the generated New World,
  land and sea, through the game's own `discover_area` effect when the campaign starts,
  once the players have chosen their countries (`on_game_started_after_lobby`); the
  computer's countries discover the New World by exploring, as in the game. No country
  record of the game changes. The world also sets the flag of the game's "New World
  discovered" event, so that this event does not reward the first Old World explorer and
  notify every player on the first exploration. A world made with the setting off is
  unchanged (the reference export reproduces). It is on the World page of both windows; the
  classic window holds it a scroll below *Before you play*.

- Keep the queue going when a world cannot be made. In both windows the failed world stays
  in the queue, marked with its error, and the next world starts. When the run ends, the
  status line counts the worlds that stay; *Run queue* tries them again, and removing a
  world or *Clear queue* forgets them. A run in which every world fails ends with the last
  error. *Cancel* still stops the queue. `rnw generate-queue` keeps stopping on the first
  failure.

- Check the colonial-nation condition on the map as it is written. Besides the map the
  generator holds, the export now reads the written `locations.png`, `definitions.txt` and
  `default.map` and refuses a world in which a passable American location touches a passable
  Old World one. The closed-ocean remainders that are recoloured only in the file were the
  one input the first check could not see; no world's files change. A Workshop report of
  Castile unable to form a colonial nation came from a world made by 1.0.0.

- Reserve space for every original area's key while constructing regions. This
  fixes an island seed whose region shrank below its required child count.

- Generate the 1337 native start from 300 years of causal prehistory: political
  transitions, eight society dimensions, reforms, relationships and migration
  that conserves population and identities. Governments, starting diplomacy,
  settlements, roads and existing stories follow the surviving historical facts.
  Read profiles, relationships, chronicles and regional history in either window
  after revealing a world, with links to places and portable import/recovery. In the
  new window a location's card has Place, Society, Chronicle and Relations tabs: traits
  as the societal values the game shows for the country with the event that shaped each,
  a timeline, and a country's overlord, subjects and agreements next to the reasons it
  remembers. A chronicle names a society that is a country by its map name, in the game
  and in the window.
  Choose historical turbulence; extraordinary peoples now seeds an ambition
  that can succeed or fail. New client obligations require real administrative
  capacity. Our History and historical opinion names are localized in all eleven
  languages. Older atlases remain readable without invented history, and the Old
  World is preserved. Target 1.2.0 uses pending epoch 61; frozen epoch 60 is retained.
  Published calibration passes; final performance, held-out validation and packaged
  delivery remain H7 work.

- Fix *Create a version* (new peoples or new resources) stopping with "The generator
  stopped" in the new window (also in 1.1.0). The line under the world had no words for a
  version being made; drawing it raised an error that ended the generator, and the version
  with it. The classic window raised the same error. A failure of the window's state is now
  recorded in the log and the last-error file and tried again instead of ending the generator,
  and a version that fails says so in the generator's words, as a new world does.

- Refuse a version of a world that an earlier algorithm made, with the reason, in both
  windows and in `rnw reroll`. A version keeps the world's land, but the generator wrote it
  with the running algorithm, so for a 1.1.0 world the new peoples, new resources and
  *Same land, change settings* could silently get other land. Their buttons are now off for
  such a world, with the reason under *Versions*, and the same words come back if an action
  is asked anyway. What made a world is read from its record, not from the release stamped
  in its code, so a world this generator made from an older code keeps its versions.
  *New world with these settings* and `rnw reroll --part land` still make a new land.
  The reason is in every official language.

- Warn on a world's page, in both windows and in the diagnostics file, when a mod after
  the world in the playset has files at the same paths as the world's, or when another RNW
  world is ticked. Either can leave the New World all Clay with empty map modes. The check
  only reads the playset and the mod folders.

- Add **Alternative History** to the hub metadata and publish all four Workshop
  categories: **Map**, **Gameplay**, **Utilities** and **Alternative History**.

- **Native Linux window startup.** A packaged Tauri window now gets the system library search path,
  not PyInstaller's bundled library directory. This lets current system WebKitGTK/ICU load its
  matching `libstdc++` on Arch and other rolling distributions.

- **No pale disc round islands in the water texture.** The first rebuild of a new coast's water
  (see the entry below) left the excess brightness that vanilla seas have 40 to 64 pixels from land
  (coasts with such neighbours lie on shallow seas) round every island and let it blend back into the
  original sea: a pale disc with an edge in the game. A shelf now ends in the far sea at three quarters
  of its reach; the background of the open sea no longer takes in the darker filled cells beside it,
  and every division rounds to the nearest instead of taking half a unit off each channel at each
  step. Where the old map was open sea the pixel is now the original with the new coast's halo
  added, which ends smoothly about 40 pixels out: nothing else of the original sea changes (it kept
  its own fine detail, which the synthetic sea lacked). On the owner's masks the mean difference from
  the original sea 32 to 64 pixels from a new island is +6.8 / +1.4 / 0 / 0 luminance units (was
  +14 / +9 / +4 / 0). A change of the water textures, so the epoch-60 reference digest is
  refreshed.

- Army strait crossings use the shortest water-only section of opposing physical shores,
  including diagonal directions. Wider or same-continent links require a real throat opening
  into wider water on both sides; short coastal land walks and parallel duplicates are excluded.
  This replaces the rejected broad 36-pixel rule that produced misplaced crossings.

## 1.1.0 — 2026-11-01

- **Hide the island groups at country selection.** The cover drawn over the New World in the game
  took only the generated locations and the ocean wastelands beside them, so the vanilla island
  groups that stay or move inside the canvas (the Polynesian strip) stood open in the covered
  ocean: the islands and the water between them showed. The covered preview already hid them. The
  cover now takes every pixel of the canvas before its groups were placed, as the preview does;
  on a test world 42 open patches (662 cells of 32 px) inside the covered ocean are gone and two
  of five cells remain, both Old World coast at the northern edge. A change of a mod file, so
  the epoch-60 reference digest is refreshed.

- **Add to queue works.** While a world is being made the next one can be prepared and queued: the
  type, seed, options and destination stay editable, *Add to queue* stays available, and a world
  added during a run is made by itself when the one before it is done (a failure or a cancellation
  stops the queue and leaves the rest waiting). The queue is listed in the middle of the Tauri
  window, under the progress while a world is made, with a button to take each world out; every
  addition says so, and the same world is not queued twice. Each continent sketched by *Choose a
  continent...* has its own *Add to queue* button (and the classic window's dialog takes several
  selected sketches to the queue), and the sketches stay on the page while worlds are made. A
  finished world no longer pulls the window away from a next world being prepared. Sketching
  continents still waits for the running world. Only the windows change: no file of a world's mod,
  so no new epoch. The queue text is in all eleven languages.
- *Expand generation into the oceans* shows only "Recommended" and an ⓘ mark in both windows;
  hovering the mark or the checkbox explains the option, and why raising *Distance from the Old
  World* is better than unchecking it when the land crowds the Old World's shores. The text is in
  all eleven languages. Only the window changes: no file of a world's mod, so no new epoch.
- In the Tauri window's world pane, the *Remove from the game* / *Add* button and the folder button
  drop to their own line when the pane is too narrow, instead of running under the scrollbar.

- A country of the New World can be chosen in the country list while the New World is covered as
  terra incognita (owner's request). Its card is no longer dimmed or unclickable, its panel is
  shown, the start and join buttons work, the context menu offers *Select* and the random
  choice is back: the cover now changes the map alone (terrain, water, borders, names and
  markers) and the mod no longer overrides the game's `multiplayer_lobby.gui` or
  `context_menu.gui`. World files change (two fewer, 868 for the reference world), so the epoch-60
  reference is refreshed; runtime behaviour at selection is not observed in the game.
- The picture of a world with its New World covered as terra incognita (the window's preview and
  the mod list's thumbnail) hides the whole canvas. It had left small uncovered discs of sea and
  island, one for each vanilla island group that stays or moves inside the canvas (Bermuda, the
  Polynesian strip and the like), which also showed where the groups went. Only pictures change:
  no file of the world's mod, so no new epoch.

- A new generator window (Tauri, with the classic Qt window kept as the fallback), a rebuilt map
  viewer with population, climate, terrain and area lenses, and a window that stays responsive
  while the game inputs are compared.
- A sixth landmass archetype, **The Wall**: a straight north-south continent or island chain with a
  mountain spine, 4% to 44% of the canvas wide.
- New settings: resource frequency sliders, the upper peasant share, a target of up to 60% of
  inhabited land in native states, and a control that keeps the New World's land away from the Old
  World's shores.
- Reworked geography: coasts, water bodies and drainage, mountains and hills, vegetation by
  climate, sea locations and their crossings, ocean currents, polar edges, and the water round new
  islands. Native states gain stronger identity cores and more varied outlines.
- Targets EU5 1.4.6 / Steam build 26300913. Algorithm epoch 60: the world bytes changed, so a world
  code made by 1.0.0 (epoch 59) can give another world. Worlds already built and their saves are
  not rewritten or migrated.
- The hub metadata adds the Gameplay and Utilities categories beside Map;
  Workshop publication tags require a separate update.

The entries below describe each change in detail.

- Cut the sea locations of a crossing like every other sea location, take the bolts of cut
  zones into the canvas and keep the land back from the canvas's boundary (owner's report on world
  `aszzsukifw`). A crossing of open water was a straight band one sea-cell wide,
  cut out of the water and divided on its own, so its cells had ruled edges and thin needles stood
  along it. A crossing is now a chain of ordinary Voronoi cells: one partition of all the water, the
  ordinary sites keep clear of the crossing's centre line, and the crossing's own sites lie along it,
  so the course is as straight as before and its cells are as irregular as any other. A remainder of
  a zone of the game that the canvas cut along its length and that is thinner than 30 pixels (it was
  20) now goes to the canvas too; twelve zones of the installed map, 0.1 % of the canvas, among them
  the bent `atlantic_north_equatorial_current10`. No land lies within 3 % of the canvas's width of
  its boundary with the game's own map (the Old World and the waters kept whole): about two and a
  half sea cells of open water for ordinary cells and a lane at the join. The land share is kept; the
  land moves inland (minimum distance from the boundary in a sample world 150 → 476 pixels). In a
  sample world cells longer than three times their width fall from 34 to 15 and the thin remainders of
  zones of the game from 12 to none. Existing worlds remain untouched.

- Let The Wall be far wider, at the expense of the continents beside it (owner report: the widest
  Wall, 14%, still had huge continents next to it). The Wall's
  width now runs from 4% to 44% of the canvas and is 14% by default. The land amount is one budget:
  the Wall takes its land first and the continents beside it get what is left (never less than 1%
  of the water beside them), so the widest Walls take nearly all the land and leave a few islands.
  A Wall wider than the amount allows keeps its land. The window's estimate of locations counts the
  Wall inside the land amount, and the width hint explains it in every language. A full export at
  the widest setting passes every sea invariant. Existing worlds remain untouched.

- Remove the dark and light discs round small islands (owner's screenshots).
  The water colour of new coasts was the mean of all vanilla coasts at a latitude, so every island
  sat in a disc of that average whose edge showed wherever the local sea was lighter or darker, and
  its halo was about twice as strong and noticeably wider than the game's. A new coast is now the
  colour of the open water around it plus the shelf the game paints at that distance, so the disc
  edge is gone (on the owner's world the difference between the new water and the original sea at
  the edge of the old disc fell from 27 to 8 luminance units, R+G+B). Foam is built the same way.
  Existing worlds remain untouched.

- Vary native polity outlines through farming corridors, similar-terrain belts and coastal
  growth alongside generalist expansion (issue #8). Small tribal groups use
  gentler preferences. Connected territories, capital membership and farming requirements
  remain enforced; population, culture and religion zones keep their existing generation.

- Give native states stronger primary-culture and faith cores through identity-aware capital
  selection and territorial growth (issue #7). Borders can retain minorities;
  great empires use milder growth preferences to preserve diversity. Population and identity
  maps, farming requirements and the population budget are unchanged.

- Let players adjust the upper peasant share from 30% to 80% at full social complexity
  (default 60%). It applies to all inhabited land: less complex and less farmable places
  remain more tribal. The total population budget and the vanilla farming threshold for
  landed states stay the same. Available in both windows and world codes.

- Let players target up to 60% of inhabited land in native states in both windows. The States
  quick choice's Many setting now targets 44% on the default presets. Explain that the planner
  can undershoot where farming and population cannot support more states; eligibility and the
  population budget are unchanged.

- Make ocean currents clear courses, or none (owner's QU3N and J4VJ reports). Where the
  generated canvas met the Old World the currents could be unreadable: three-location stubs, arrows
  pointing across their own lane, clusters pointing different ways, neighbours driven head-on, a straight
  prepared line with no current beside a cluster of arrows. A navigable deep cell now carries a current
  only when the cells form a directed path: either a continuation of a current of the game (arrows follow
  the path round bends, water that enters a cell leaves it, a well supported current is never split by a
  lone contrary zone, short branches and pieces are dropped, a short piece is kept only if it joins two
  currents of the game), or a straight crossing of open water through the generated oceans, which takes
  the direction of the game's gyres at its latitude and place wherever they are clear (and has no
  current where they are not) and runs through its shallow strips; a wide cluster of deep cells, a sea
  and not a lane, carries no arrows. The other lane cells stay navigable deep ocean without an arrow, so
  routes, ports and names do not change. In world QU3N 182 of 248 lane cells carry a current; no two
  neighbours point at each other (14 pairs did) and no arrow points against a zone of the game that
  touches it. Existing worlds remain untouched.

- Merge sliver sea locations into their neighbours. Some generated sea locations were
  long needles or crescents (one 212 × 20 pixels) because a coast, a crossing or
  an island group's footprint cut a cell into pieces that were merged only by area. A sea cell thinner than
  a fifth of the cell spacing, bordered mostly by other sea cells, now joins the neighbour it shares most
  with; straits, bordered by land, stay. A sample world drops from 1,547 to 1,494 sea cells and has no thin
  cell left between others. Existing worlds remain untouched.

- Take thin remainders of trimmed sea zones into the canvas. A location of the game that
  the canvas cut along its length stayed as a needle among the generated waters (in a sample world
  `pacific_south_current2`: 29 % of the zone left, 12.6 pixels thick, touching six neighbours). A remainder
  thinner than 20 pixels now goes to the canvas, as one under 3,000 pixels already did; two zones of the game
  are replaced in every world. Existing worlds remain untouched.

- Keep generated American coastal sea areas from bordering passable Old World seas
  (issue #9). Ocean areas now form a connected boundary at
  those contacts, preserving routes while colonial overseas eligibility remains
  available for North and South America. Final-map validation rejects any
  remaining passable American/Old World contact.

- Narrow the places where ordinary continents meet the north and south map edges. Land locations near the poles grow larger, and all locations
  touching a polar edge are impassable. The Wall retains its continuous endpoints;
  existing generated worlds are unaffected.

- Add a control that keeps the New World's land away from the Old World's shores.
  Advanced → Land → Distance from the Old World lifts the land density in the middle of the canvas, so
  continents move toward the middle of the ocean while the amount of land does not change; on the
  installed canvas the land's mean distance from the canvas edge goes from about 1,540–1,920 pixels to
  about 2,340–2,390 across the range. It is 0 by default, which leaves every world as it was; The Wall and
  land drawn from an image ignore it. It is in both windows, in all eleven languages and in world codes.

- Widen the expanded ocean across the Pacific and move the islands that continents would cover. The expanded canvas now reaches the whole Pacific side of the New World: the
  Polynesian islands before the map's seam, the open ocean to both polar edges and the water east of New
  Zealand, bounded by round contours well clear of the Old World (nothing is generated between New
  Zealand and Australia). The Atlantic side is unchanged. The Polynesian islands, and the few isolated
  ones the new shape encloses (the northwestern Hawaiian atolls, Pitcairn, Rapa Nui, Bermuda, St Helena,
  Ascension, Tristan da Cunha and Gough), are no longer holes that land must go round: the land is
  generated first, then a group of islands with room around it stays where it is, and one the land would
  cover moves, whole and with its coast zones, to the nearest free ocean, keeping its latitude where it
  can, together with its heights, ground materials, mountains, vegetation, water colour and foam,
  locators and ports. Because the canvas is 17 % larger, the
  presets' land shares are 15 % lower, so a world keeps its land and about its locations (continents now
  340 ‰, supercontinent 460 ‰, small continents 255 ‰); the location estimate is refitted on seven
  full exports. Existing worlds remain untouched.

- Keep a location's vegetation consistent with its climate (issue #4). The
  biome classifier smoothed vegetation votes across neighbours of other climates, so a cell could
  get a climate/vegetation pair that no Old World location has (for example desert in a
  subtropical climate, or forest in an arid one). The votes are now smoothed as (climate,
  vegetation) pairs and a cell's vegetation is chosen among the pairs of its own climate, with a
  wider neighbourhood where the climate has no vote nearby. In four exports of the installed game,
  3 to 14 cells per world carried such a pair and now none does; about 3 to 4 % of cells change
  vegetation, almost all on climate borders, and no climate changes. Existing worlds remain
  untouched.

- Rework mountains and hills. Ranges are now continuous chains of one
  realistic width that fork and arc, with massifs of different heights, passes between them and
  lower secondary ranges, instead of broad one-height blobs cut into segments. Crests carry
  erosion-like ridges that grow on high ground and leave valleys smooth. Vanilla's mountains owe
  most of their relief to 3,706 mountain stamps that the game adds to its heightmaps; the generator
  now places the same stamps at vanilla's density, sizes and strength (a quarter more), turns them along
  each range's axis and adds them as the game does, so mountains have vanilla's local relief and slope
  by height class instead of about two fifths of them (the first rebuild compared with the heightmaps
  without the stamps and was too gentle: in game, mountains looked like hills). The stamps' material
  layers are laid over the mountains, giving the eroded pattern of crests and valleys that vanilla's
  mountains have. The ground has the fine grain of vanilla's: the terrain's detail noise follows the
  installed heightmaps' roughness from 64 down to 4 pixels. Lakes no longer stand in cones of rising
  ground that lowered the interior wherever lakes overlapped, and hills rise from a lake's shore instead
  of out of a flat bowl. Rivers, cell topography and biomes follow the new relief. Existing worlds remain
  untouched.

- Rework coasts, water bodies and drainage together. Coasts are drawn from a
  bent density field, so continents have capes, hooked peninsulas and gulfs with narrow mouths
  instead of rounded blobs. Lakes now follow the installed game's own: about 11 per million
  land pixels, from small ponds to lakes of 17,000 pixels or more (the 1.0.0 generator made
  one tenth as many, none above 4,000), with the lobes, bays, arms and islands of real lakes
  rather than ovals. The physical map in both windows draws a lake as a level surface in the
  land instead of a pit with walls, so lakes no longer read as craters. Inland seas, lagoons behind spits and gulfs with one narrow
  strait appear on most continents, and some seeds join landmasses by isthmuses. Rivers now
  flow into lakes and out of them: each lake gives one outflow river from its lowest rim.
  Largest lake defaults to 25,000 pixels (range up to 60,000) and its help text, which said
  larger enclosed water stays sea, is corrected in every language. A strait that runs through
  the map's display seam is no longer written as a crossing (the game has no such row);
  it stopped one island world from exporting. Existing worlds remain untouched.

- Fix The Wall's thin, ruler-straight stretches. With
  "Allow gaps" off, a straight strip of land, a quarter of the envelope wide, was forced down the middle, and wherever the
  coast field (little land, high irregularity) left the wall's own land empty, that bare strip was
  all that remained, with straight vertical cuts where coasts reached the edge of the wall's envelope.
  The forced core is now a broad ridge that drifts and swells along its length (never narrower than
  0.6 of the envelope's half-width), its edge is ragged like any coast, coastal noise fades toward the
  envelope's edge instead of being cut off there, and the mountain spine follows the core. The land
  share control now thins the side land only: it never takes land from the wall, which keeps the share
  it is sized for. Existing worlds remain untouched.

- Let The Wall go around protected islands instead of needing a full-height corridor free of them. The wall had to sit in a column band with no protected pixel
  from the north edge to the south edge, which on the installed expanded canvas is 17.6% of its
  width, and the width and position controls shared what was left after the envelope's half-width
  (2.6% of the canvas at the largest width, so the position control barely moved the wall). The
  position control now spans the whole mostly open band of the canvas (3,500 pixels of 10,075 there). The
  wall is a straight line at the chosen position wherever its envelope fits, and a smooth detour,
  never steeper than one pixel a row, around the island or the whole group of islands in its way,
  returning to its position beyond them. No route from edge to edge is still rejected. Existing worlds
  remain untouched.

- Give The Wall's secondary continents a broader procedural placement field, so
  seeds can leave whole side regions as ocean instead of repeatedly scattering
  land through the same canvas pockets. Existing worlds remain untouched.

- Simplify generation progress: show the current stages once in the main stage list,
  keeping the time estimate below the progress bar and a general generation status in the
  inspector. Rework ETA around the remaining parallel stage dependencies and current reference
  timings, with a stable completion deadline and bounded corrections for overdue work. Learn
  stage costs from recent successful local runs of the same preset/build and execution limits;
  exclude cached geography and waits for the game. Both windows show the estimate for the
  current world in a queue too. World output is unchanged.

- Add The Wall: a procedural straight north-south continent or island chain with a mountain spine,
  impassable polar end locations, procedural coasts and extra continents/islands on
  either side. Natural straits emerge from the density field, seed and geography
  settings; a checkbox can require continuous land. Both windows offer width, position,
  coastal irregularity and ridge height controls; world codes preserve them. Remove mandatory polar ocean margins
  from ordinary and image-based generation so land can naturally reach the map edges.

- Keep the window responsive while choosing worlds: compare game inputs in the background,
  reuse file hashes and game names, calculate the Tauri map's relief and region names in a
  worker, and draw classic-window maps on demand with only the latest request queued.

- Target 1.1.0, with algorithm epoch 60. Add separate 0–3× frequency sliders
  for all 34 ordinary New World resources in both generator windows and all official
  languages. Keep the precious-resource control, vanilla default weights and habitat
  matching. World codes preserve each weight. Explain relative placement probabilities
  and unchanged production per location; fail explicitly when no enabled resource fits.

- Add the Gameplay and Utilities categories alongside Map to the hub metadata.
- The generator's window is now a Tauri window (ADR 0011), in the Workshop hub and
  the Linux package; the Qt window stays as the classic window. The classic window
  opens by itself where there is no web view (no WebView2, as in Proton; no
  WebKitGTK), and on request: Use the classic window in Settings, `--classic` or
  `RNW_WINDOW=classic`. Self-tests check both windows; the packages carry the
  window's licence notices, including Microsoft's WebView2 loader. The window looks
  the same on every system: a workbench sized to sit beside the game (default 1160×740, minimum
  860×560). A searchable library with multi-select, a view in the middle and an
  inspector; both side panes resize and hide (Ctrl+B, Ctrl+I). A world opens on its
  map, with its details, versions, files, lenses, legend, search and notes in the
  inspector. The new world is set in the inspector, exact values as bars to drag,
  above the location budget and Generate; the middle shows the continent sketches
  to pick from, the land image, progress with its stages, and the outcome. Language
  and appearance change without a restart.
- The classic Qt window, the fallback where the new window cannot open (as in
  Proton), draws the maps as the new window does: the physical map under every
  lens, states with tribes as an option, the same palettes (one file for both
  windows), names, cities, capitals and riches at every zoom, a legend that
  lights, isolates and zooms, one search with areas, a pinned location card with
  links, lens keys 1–0, copying the view and saving the lens as drawn. Its library
  gains the filter and views, its new world a budget meter, and it answers the new
  window's shortcuts. Sea and area names use the game's names in both windows.
- Rebuild the map viewer: WebGL lenses with sharp borders at any zoom, place
  names, minimap, hover and pinned location cards, legend isolation and search
  that zoom to their match, area search, linked comparison and copying the view.
  The physical map opens first and lies under every lens: shaded relief,
  softened vegetation and climate, sea depth, region and sea names, cities.
  Countries shows states as the game does, with tribes as an option; resources
  are coloured by family, mark riches and name each location up close; cultures,
  religions and areas keep neighbours apart and are named where they are
  broadest. A saved map picture is the lens as drawn.
- Add population, climate, terrain and areas lenses to the atlas, the Qt maps,
  PNG export and the CLI; the existing lenses draw the same bytes.
- Keep a chosen game folder's discovered build instead of showing it as unknown.
- Keep the New world library action visible when the platform has no matching icon theme.
- Replace the hub avatar with the owner's in-game map and generator screenshot design.

## 1.0.0 — 2026-10-29

- First stable release: locally generated continents, terrain, climate,
  rivers, seas and native societies, with the vanilla Old World preserved.
- Includes five landmass archetypes, optional ocean expansion and extraordinary
  societies, regional stories, formable countries and colonial names.
- Ships the generator, atlas, world library, World Codes and all eleven official
  EU5 languages. Worlds remain local; release packages contain no game assets.
- Targets EU5 1.4.5 / Steam build 26211608, with Across the Pillars geography
  adaptation. The DLC remains optional. Algorithm epoch stays 59; pre-1.0 worlds
  and saves are preserved rather than migrated.
- Keep the Total Chaos controls aligned and explain visibility refresh through
  EU5’s main-menu Mods manager in every official language.
- Adopt release-based versioning, pin candidate builds to exact commits, and
  include SHA-256 manifests with source and platform archives.
- Publish the hub as Random New World (RNW), with permanent mod ID
  `sirstarch.randomnewworld`; retain the local `rnw_exp_hub` folder and safely
  update hubs carrying the earlier internal ID.
- State unsigned-Windows and campaign compatibility limits in the player guides.
  Remove build-machine installation receipts and absolute bytecode filenames
  from the Windows runtime package; include reports for the two project binaries.

## 0.13.23 — 2026-10-28

- Keep the world basics buttons aligned when Total Chaos produces custom values.
- Visibility changes now tell players to close and reopen the Mods manager from
  EU5's main menu so the game reloads the updated world mod, without restarting
  EU5. The updated instructions are included in all ten translated catalogs.

## 0.13.22 — 2026-10-28

- Adapt Across the Pillars to generated worlds on EU5 1.4.5: retain its eight
  legendary-city expeditions, two treasure fleets and their location-bound
  callbacks through the geographic remap, preserving the DLC requirements.
- Gate the historical Brazilian-to-New-Amsterdam diaspora event, consistent with
  other literal American historical incidents. Dynamic colonial situation content
  retains vanilla behavior. Epoch 59; existing worlds and saves are preserved.

## 0.13.21 — 2026-10-28

- Sacred-centre theocracies now start with compatible marriage and heir-religion
  laws and a native assembly, read from the installed game's precedents.
  Generation rejects incomplete or incompatible government institutions before
  installing a world. Existing worlds and saves are preserved.

## 0.13.20 — 2026-10-28

- Restore the previous periodic primary terrain-source extension at the owner’s
  request after the unpadded version exposed a more prominent map seam. Epoch 57.
- Retain independent river watersheds, genuine-outlet validation and all mechanical
  wrap corrections. Rendering of this combination remains unverified in game.

## 0.13.19 — 2026-10-28

- Generate independent river catchments on either side of the display seam, with
  closed boundaries and genuine sea/lake outlets. Preserve the expanded canvas
  and mainland crossings. Epoch 56.
- Follow every main river to actual water and reject inland endings. Encode the
  planned network without cutting pixels or inventing sources at the seam.

## 0.13.18 — 2026-10-28

- Remove the extended terrain sources and shifted primary placements used to conceal
  the world-edge crack, now reproduced by the owner in vanilla. Retain continuous
  geography, location identities and all route/hang corrections. Epoch 55.
- Separate the terrain crack, river discontinuity and locator diagnostics in a
  dedicated evidence dossier, including an owner-run historical comparison plan.

## 0.13.17 — 2026-10-28

- Build remote states around local farming centres before allocating population. Landed
  countries must meet the installed vanilla Americas’ minimum peasant population and share;
  insufficient settlements remain tribal, including would-be confederation members.
- Give disconnected groups of landed countries a trading town and local market, reusing
  existing centres within a group. Preserve the population budget and vanilla expansion rules.
  Epoch 54; actual income and subsequent AI development remain unverified in game.

## 0.13.16 — 2026-10-27

- Build ocean routes from the generated shores and live current entries. Interior remnants
  of the old world's current footprints no longer impose curved fragments on the new map.
- Require an opening of useful width where a deep route meets other water; a few touching
  pixels no longer count as a completed ocean route. Natural shallow channels keep their
  contacts. Isolated one-location gaps remain navigable ordinary sea without current arrows.
- Align unambiguous current passages with their actual exits, including ordinary water at
  their ends. Preserve the generated land and relief. Epoch 53.

## 0.13.15 — 2026-10-27

- Keep sea classifications consistent with planned ocean lanes when closed water is folded,
  complete any route ends introduced by later crossings and check navigation before the
  expensive export stages. Epoch 52.
- Keep location, province and area replacements separate when vanilla reuses a name. Choose a
  drawable river-fragment start when the first one leaves no room for a confluence marker,
  without changing the physical river or discarding its drawing pixels.
- Check the location limit against final identities, avoiding a premature refusal when generated
  sea cells share a retained ocean identity.
- Show generation errors in a selectable, scrollable panel with explanations for ocean,
  river, location-limit, file and unexpected errors. Offer an immediate retry with a different
  seed and the same settings.

## 0.13.14 — 2026-10-27

- Align currents on straight designed crossings to the band's geometry. The direction is
  chosen consistently along each band from its continued source currents; ambiguous broad
  junctions retain their interpolated flow. Epoch 51; game rendering remains unverified.

## 0.13.13 — 2026-10-27

- Plan useful crossings over the generated water before partitioning sea locations. Their
  centre lines are simplified through unobstructed water and their bands become connected
  sea-cell geometry, while actual currents still require a reachable existing source.
- Join small, disconnected retained-ocean remainders to an adjacent navigable sea when they
  share an edge; preserve principal vanilla identities and landlocked remnants. Epoch 50;
  in-game rendering and navigation remain unverified.

## 0.13.12 — 2026-10-27

- Plan crossings between distant shore stretches and retained water from the generated geography,
  remove isolated closed-water slivers before zoning, and name impassable water for its area.
- Partition generated sea cells by Euclidean distance so their shared borders do not develop the
  large Manhattan-distance elbows seen in the owner's hover screenshot. Epoch 49; game rendering
  and navigation remain unverified.

## 0.13.11 — 2026-10-27

- Build sea locations against the installed game's current bands, rather than approximating their
  shape with unrelated sea-cell borders. Complete cyclic open-ocean ends, align unambiguous narrow
  currents with their routes, and reject currents without a reachable, unambiguous source. Epoch 48;
  offline candidate, with no new EU5 launch.

## 0.13.10 — 2026-10-27

- Set up sacred centres as theocracies without inheriting monarchy laws and
  privileges, following the vanilla Tibetan setup. Epoch 47; offline candidate.

## 0.13.9 — 2026-10-27

- Keep vanilla's `ai_balanced` as the normal baseline. Countries receive a more
  distinctive personality only for explicit threats, rivalries, diplomatic ties,
  a great empire's designated prey, or a defining society archetype; a coastline,
  population advantage or ordinary border alone no longer forces a personality.
  The report includes every selection signal, including confederation membership.
  Epoch 46; offline candidate, with no EU5 launch.

## 0.13.8 — 2026-10-26

- Choose generated countries' vanilla AI personalities from their generated context: comparative
  population and technology, borders, markets and coasts, empires' prey and threats, rivalries,
  alliances, subjects and extraordinary-society archetypes. Selection is deterministic and each
  country's profile has an auditable reason in `report.json`; Balanced remains for ordinary border
  states without a defining strategic signal. Epoch 45; offline candidate, with no EU5 launch.

## 0.13.7 — 2026-10-26

- Generated landed New World countries receive a reproducible AI personality assignment, sampled
  by the frequencies of explicit country assignments in the installed game's 1337 setup. Pop-only
  tribal groups remain unassigned; vanilla personality definitions and the setup file are read
  locally and validated. Epoch 44;
  game behavior not yet rechecked.

## 0.13.6 — 2026-10-26

- Correct the mod defects identified in the owner's completed EVXP campaign.
  Treaty comparisons use native scoped numeric values; generated treaty files
  carry UTF-8 BOMs and geography labels in all eleven official languages.
- River drawing fragments stop before the final raster column: EU5 discovers
  components with bounded coordinates but its line walker can normalize that
  column's next neighbour to column zero, joining unrelated drawing fragments.
  Physical drainage, carved valleys and continuous location identities stay intact.
- Write exactly one VFX locator per final location, including retained oceans;
  reject duplicate identifiers and incomplete whole-world VFX coverage.
- Derive starting town templates from the installed guild-capacity rules and
  generated development/population. Initial guild levels fit even at the lowest
  market access; vanilla building rules and generated population are preserved.
  Epoch 43; offline candidate, with no new EU5 launch or save migration.

## 0.13.5 — 2026-10-26

- Generated locations keep one identity across the map's raster edge, as vanilla does.
  Removed the legacy seam split for land, sea, lakes and wastelands, including from the
  land cache. This removes the artificial straight border and the extra adjacency in
  the owner's immediately reproducible Towa troop-raising case. Mainland, relief and
  rivers are preserved; no engine patch or replacement geography. Epoch 42. Written
  output and reproducibility checked offline; the owner's
  [22F4 test](experiments/068-continuous-location-identities/README.md#owner-crossing-test-22f4-2026-10-26)
  verifies post-fix troop movement across the seam without a hang (C380).
- When a generated region has no counterpart for a former sea area, setup discoveries
  and script references use the same geographic replacement binding. A vanished
  discovery area no longer retires an otherwise retained country. Existing validators
  still reject unresolved references and incompatible destinations.

All notable changes to Random New World. The project has one product version ([ADR 0003](docs/adr/0003-versioning.md)): `0.MINOR.PATCH` is development, MINOR rises when the owner accepts a roadmap phase in game, and the first Steam Workshop publication will be 1.0.0. Any change to generated output raises at least PATCH. A change to any file of a world's mod other than `.metadata` also starts a new **algorithm epoch** with a new reference world.

`C###` numbers refer to the [claims ledger](docs/research/claims-ledger.md). Evidence labels (`[V-GAME]`, `[V-EXEC]`, …) are explained in [CONTRIBUTING](CONTRIBUTING.md#evidence-labels). Entries without an in-game result have been checked offline only.

## [Unreleased]

- Generator interface improvements:
  - Fixed preview zoom and drag on the "World" tab. The scale constraint now considers both width and height rather than width alone, enabling smooth wheel zoom, scroll drag, and double-click fit on height-constrained preview views.
  - Added an "About…" dialog with application details, version, author, licence, legal disclaimer, and links to the GitHub repository, documentation, issues tracker, and changelog. Accessible from the main window header and the Settings dialog, translated into all eleven official languages.
- Two draws in the window's world type list. **Random** draws one of the five world types, and **Total Chaos** draws a type and every Advanced value within its playable range. Random draws its world type again at each press of the random button; Total Chaos is drawn only when chosen, and its button press only gives a new seed. Both draws stay inside the location budget. The world made is an ordinary world of the type drawn: its values travel in its world code, as any other choice does. No generated output changes. Checked offline: three Total Chaos worlds were made on build 26142040 and finished without error.
- Generator progress keeps its stage description on one fixed-height line, shows a live ETA that adapts to the weighted stage pace measured in the current run, and uses the same rounded percentage in the world list and progress bar.
- The Workshop description is rewritten for players, as EU5 mod pages are: what a world holds, a quick start, the window's choices, why there is a program, the limits, a FAQ and links, with an emoji for each section. It is kept in Steam's markup, ready to paste, in all eleven official languages, and each text is checked against Steam's limit of 8,000 bytes (C277).
- Generator library: select several worlds with Ctrl/Shift or Select all, then remove their mods from EU5 directly below the list. Codes and pictures stay in the library. A separate bulk deletion asks once before deleting library records and kept files. Selection survives list updates; removal no longer needs the game installation, and deletion errors stop the batch visibly (C266). The library panel takes its width from the splitter alone: its texts wrap or clip instead of setting a minimum, so a wide font or an error that names a long Windows path no longer widens the window past 1080 pixels.
- Repository prepared for publication: new README, changelog, contribution, security and conduct documents, issue and pull-request templates, documentation index. Completed agent hand-off notes were retired, and the history was cleaned of local machine details.
- Windows fixes found by the first CI run on Windows. The window's self-test closes its log before removing its temporary folder. The atlas cache also compares file sizes, so a file rewritten within one clock tick is not served stale. Tests now write fixtures with LF line endings, escape Windows paths in Steam's VDF, use short test ids, and wait for the window to enable a control before clicking it. A notice about a world's visibility is no longer wiped by the refresh that the change triggers.

## 0.13.4 — 2026-10-26

- Every generated map mod now has a short description introducing Random New World Generator, giving its world code, and pointing players to the Steam Workshop to create their own worlds. Metadata-only change; algorithm epoch 41 is unchanged.

## 0.13.3 — 2026-10-26

- Installed RNW worlds are recognized automatically from their world code or saved recovery data (C354–C356). Their existing mod folders and playsets stay intact. New application-generated worlds carry a library recovery bundle in `.metadata`, including their atlas, pictures, original record and input manifest; private notes, favourites and user tags stay in the library. Recovery checks the record and asset hashes before committing a full entry, handles metadata-first copies, and preserves existing names and notes. The open window notices new mods and library entries without resetting selection or unsaved notes. Legacy worlds with only a code remain usable, with their missing build/record shown honestly. All new wording is translated into every official language. The Maps panel yields its width to the splitter so wide translations and large desktop fonts cannot expand the window past its minimum supported size. This changes application behaviour and metadata only: algorithm epoch 41 and its reference world remain unchanged.

## 0.13.2 — 2026-10-26

- Ocean routes continue to another lane, coastal water or retained navigable water instead of ending inside impassable ocean (C349–C352). The 657Q report reproduced four open-ocean ends; the gap beside Ruaziasleir Coast is one closed internal cell. The planner opens it and completes the other two ends, adding eleven lane cells in total. Continuations prefer the incoming course's outward direction and cannot loop straight back into their own stem. An independent export check rejects reachable lanes with an open-ocean dead end. Version 0.13.2, algorithm epoch 41; checked offline, with no EU5 launch.

## 0.13.1 — 2026-10-26

- Map object VFX locator generation completed for all expanded ocean locations (C348). When `expand_oceans` adds new `rnw_ocean_*` wasteland locations to `definitions.txt`, their positions are now explicitly exported into `generated_locators_vfx.txt`. In vanilla EU5, all 28,573 locations require a VFX locator; with ocean expansion, all 30,565 locations now have full 1:1 locator coverage, eliminating the engine's `map object locator "vfx" is incomplete!` startup error. Validated offline with an explicit test in `verify_locators`. Algorithm epoch 40 with updated reference world digest.
- Diagnostic audit of corrupted country-name formatting in TR46 observer logs (`error.log:1210–1269`, C347). Traced via binary analysis of `countryname.cpp:1135` and `pdx_text_formatter.cpp:807` to vanilla Jomini country acronym formatting on an Old World Moroccan civil war (`game.log:7389`), producing control-byte-polluted initials `\x15.\x15.W.R.`. Attributed to vanilla engine; no generator defect.

## 0.13.0 — 2026-10-25

- In-game acceptance of the cylindrical wrap, impassable mountain relief and TR46 candidate fixes by the owner (C345-C346). ADR 0003: MINOR rises when a roadmap/campaign phase is accepted in game. The visual seam at the horizontal map wrap is confirmed absent in game (TR46-06a CLOSED [V-GAME]). Impassable mountains are visibly improved and accepted for release (TR46-01 / TR46-02 ACCEPTED [V-GAME], further aesthetic ridge improvements postponed to post-release). No file of a world changes; epoch stays 39 and the reference world is the one of 0.12.9.

## 0.12.9 — 2026-10-25

- Tordesillas follows the continuous New World longitude axis across the raster seam. Its side selection, line moves, side-swap estimates, map shading and final province claims use the same generated coordinates; the western continuation of a mainland is no longer treated as east merely because it is drawn at raster right. Vanilla religion, ownership, existing-claim and province-granularity rules are preserved. Coordinates are immutable native geography/value data, with no campaign startup repair or engine modification. Offline candidate; engine behavior remains unobserved.

## 0.12.8 — 2026-10-25

- Compatible connected impassable land becomes one location before provinces and areas are built, retaining distinct biome boundaries. Generated highlands gain fine eroded height detail sampled from the installed vanilla mountain sources, with continuous wrap support and preserved river lines. Epoch 38; checked offline, final game appearance remains unobserved. Administrative regrouping can rebind native cultures/religions and their dependent start data.

## 0.12.7 — 2026-10-25

- Nearby coasts now receive short local shipping connections as well as global access to the Old World; retained navigable boundary contacts continue into open water. Connected closed water is no longer divided into arbitrary 48-cell oceans with unrelated names. Script replacements preserve ports and passable water, fixing the inland landfalls found in TR46's western voyage. Epoch 37; checked offline, engine navigation and expedition outcomes remain unobserved.

## 0.12.6 — 2026-10-25

- Primary edge heightmaps now contain periodic source pixels beyond the world boundary, with matching source dimensions, cached geometry and original instances. Interior height/material samples keep their alignment and values. This replaces outside-only duplicate placements and provides primary source coverage for boundary vertices and tested page halos while preserving full mainland wrap. A stale layer size now fails before writing. Epoch 36; checked offline, the reported terrain crack remains open pending engine appearance.

## 0.12.5 — 2026-10-25

- Rivers crossing the map seam now receive the starts and tributary markers required by each planar raster fragment. The continuous drainage, channel widths and carved valleys are retained; networks away from the seam keep their exact raster codes. This addresses TR46’s missing river-source errors without changing the continent shape or restoring a seam strait. Epoch 35; checked offline, engine rendering remains unobserved.

## 0.12.4 — 2026-10-25

- Replaced coastlines now include their offshore visual footprint. Height and material synthesis covers the old shelf beside removed islands, including across decal and map boundaries, while retaining Old World land. Water colour and foam are rebuilt where the changed coast affects their distance field and blur, even outside the replaced location colours. This addresses the remaining original-Alaska shelf rims near Chukotka reported in TR46. Location identities and land generation are unchanged. Epoch 34; checked offline, rendered result not yet observed in game.

## 0.12.3 — 2026-10-25

- Continent-scale noise now interpolates with 16-bit fractions. The former 8-bit fractions held the large-scale field flat for about 14 pixels, then jumped, producing long straight teeth on thresholded coasts. This fixes the field itself, including climate and relief that use the shared kernel; no post-generation coast smoothing. Epoch 33.
- Heightmap placements now continue periodically outside both horizontal map edges, in the terrain cache and instance files. The vanilla decal contract excludes a placement's upper endpoint, which left the world-edge sample and outside page halos without their opposite-side terrain. Original textures and interior placements are retained; no shader/engine change. Offline tests cover boundary/halo samples and unchanged interior coverage. The owner's 0.12.2 screenshot confirms a physical crack; the new placement's engine result is still unverified (C293–C295).

## 0.12.2 — 2026-10-25

- The New World can continue across the map edges as one continent. Removed the mandatory seam strait that had isolated the former-Alaska part near Japan, including its coast ramp and exclusion of drawn land. Terrain sampling and fine detail now continue across the wrap; water distance, foam blur and detail use horizontal wrapping, and roads cover contacts across the seam by the short route. Existing worlds retain their geography; newly generated worlds use epoch 32. Checked offline; the new seam terrain and road rendering have not been observed in game (C289–C290).

## 0.12.1 — 2026-10-25

- Seeded placement of the land-noise lattice removes fixed high-variance positions that favoured recurring island outlines in the narrow former-Alaska part of the canvas near Japan. One origin applies to the whole New World across the map wrap; there is no regional land quota or island deletion rule. A lobe may stay ocean or contain islands according to the seed. Existing worlds keep their maps; newly generated worlds use epoch 31 (C286–C287, checked offline).

## 0.12.0 — 2026-10-24

- **Optional ocean expansion (S2).** *Expand generation into the oceans* is enabled by default and recommended. It adds a fixed ocean sector around the Americas, preserving the Old World and protected islands; unchecking it uses the original coast-following canvas. The choice travels in the world code, sketches, land templates and rerolls. Codes made before 0.12.0 select the original canvas. The canvas grows from 37,978,627 to 53,240,944 pixels on the current map contract.
- Surviving closed oceans keep their vanilla names in every official language. Connected retained and generated water shares one location; land or lanes separating it produce separate connected locations with the same name. Disconnected ocean remnants no longer exclude an entire closed ocean from generation. Passable water, currents and ports remain separate.
- Location density and the window's budget estimate account for the larger domain. Discovery uses the actual generated coastal areas, including new ones and omitting regions that have become landlocked. A short gap crossing two sea zones no longer produces an invalid army crossing. Epoch 30; expanded-map engine results remain unverified.
- Verification uses the project's Python 3.12 environment explicitly, resolving the previously recorded type-checker discovery failure.

## 0.11.6 — 2026-10-24

- **L1: the generator's window in every official language.** The window starts in the language Steam runs the game in, or in the one chosen in Settings (the change applies at the next start). All its texts are translated into the ten other official languages: export stages, messages and errors included. Numbers are grouped the local way. Maps show place names in the window's language, and, when the game is installed, the game's own names for cultures, religions, resources and terrain. Every language is tested to fit the smallest supported window size. The atlas beside a world's mod is now format 2, which stores names as phrases; format 1 is still read. The mod's files are unchanged, so this stays in epoch 29.
- The Workshop description is written in every official language (`docs/workshop/`), each checked against its English source. A mod's metadata holds one language only, so the mod list's titles stay English (C276).

## 0.11.5 — 2026-10-24

- **L1: the world's mod in every official language** ([localization](docs/localization.md), C268–C274). The stories, formable countries and exceptional places are translated into Brazilian Portuguese, French, German, Japanese, Korean, Polish, Russian, Simplified Chinese, Spanish and Turkish. Their English was rewritten first: fewer repeated devices, more of the country's own voice, as the game's events have it. Generated names follow each language's geography: *Море Кайра*, *Kaira-Meer*, *Mer de Kaira*, *カイラ海*; parts of a sea are *Западная часть моря Кайра* or *Golfe d'Akaira du Nord*; formables are *Кайрский союз*, *Kairanische Union*, *Unia Kairańska*; colonies are *Новая Кайра* or *ヌエバ・カイラ*. Russian, Japanese, Korean and Chinese write every generated name in their own script, as the game does with its American names. Country adjectives take the form the game's texts complete in Russian, Polish and German. A release check fails on a missing or outdated translation. Epoch 29, reference world of 814 files.

## 0.11.4 — 2026-10-24

- **N5: region and area keys by physical content** ([design and audit](docs/research/n5-region-keys.md), C262–C265). The 14 American land regions and 135 land areas keep their vanilla parents, and each key goes to the generated part whose climate, relief, coast and relative size are closest to the vanilla template, chosen by one global integer assignment (position only breaks ties). On three worlds the total template difference falls by 18.91 to 22.26 per cent, and the Old World is unchanged. Region parts are built before names are assigned, with room for every original area. Epoch 28, reference world of 814 files.

## 0.11.3 — 2026-10-24

- Fixes from the 0.11.2 sitting and the seed-210 regression ([046](experiments/046-sitting-fixes/README.md), C257–C261):
  - The sea planner no longer emits an empty area when an ocean area survives entirely in vanilla water.
  - The lobby handles an absent selected country through an optional saved scope.
  - Map-name replacements occupy their installed localisation paths and no longer define the same keys in an extra file.
  - The window reports completion only after its library holds the finished world.
- Epoch 27.

## 0.11.2 — 2026-10-24

- **R7d: more varied societies** ([natives](docs/natives.md), C251–C253). Besides the great empire, a world can now hold:
  - a sea league: 3 to 5 republics on one sea, allied in a ring, with a city and a market at the hub's port;
  - a highland confederation: 3 to 6 tribes of one faith in one `tribal_confederation`;
  - a fractured realm: 3 or 4 rival centres;
  - a sacred centre: a theocracy among rivals of its faith.

  Each uses records the vanilla 1337 setup already uses, with a cost beside every gain. With the chance set to 0 the world is byte for byte as 0.11.1 made it. The window calls the control *Extraordinary peoples*. Epoch 26, reference world of 792 files.

## 0.11.0 – 0.11.1 — 2026-10-24

- **0.11.0:** `[V-GAME]` the sea phase (S1) is accepted in game. The owner observed the 0.10.14 world for four months of game time, and the logs show no port, lane, topography, current or crossing error (C248).
- **0.11.1:** the game's closed ocean zones have no unit or combat locators, and generated closed zones no longer have them either. The lobby's scripted GUI checks `country_exists` before asking about the selected country, which removes 263 script errors a session (C249–C250). Epoch 25.

## 0.10.12 – 0.10.14 — 2026-10-24: sea geography

- **0.10.12:** ports are assigned so that every coastal sea zone has one wherever the land allows. Water is named by its shape (seas, gulfs, bays, straits, coasts, capes, island waters), and the game's ocean areas keep their names in every language. The game's own kinds of water are used: deep ocean, inland sea, narrows. Generated deep water continues the game's currents (C232–C240). Epoch 22.
- **0.10.13:** `[V-GAME]` the open ocean is closed to ships, as in the game: lanes one or two cells wide follow the currents, and the remaining deep water is impassable `ocean_wasteland` (C241–C244). Epoch 23.
- **0.10.14:** strait crossings. Landmasses that come within 36 pixels are brought together to a narrow channel, and every pair of lands across a run of at most 9 pixels of one sea zone gets an `adjacencies.csv` row (C245–C247). Epoch 24.

## 0.10.0 – 0.10.11 — 2026-10-23: New World content

- **0.10.11:** offline audit of N0 to N4 ([audit](docs/research/n0-n4-audit.md)). Three faults are repaired: `province_definition:` references are remapped, hidden story events have titles, and the DLC pyramid models of Teotihuacan and Cholula are no longer moved to random places. The export now refuses a world in which a vanilla script object vanished without a decision (C222–C231). Epoch 21.
- **0.10.10:** *Contact across the ocean* and *Colony becomes a country* stories, a *Postcolonial federation* formable and 70 colonial names (*New X*, built from each region's generated name) (C218–C220).
- **0.10.9:** four stories: *Harvest and food supply*, *Route and market*, *Great alliance*, *Empire and periphery* (C215–C217).
- **0.10.8:** four formable families: *Highland confederation*, *Maritime league*, *Cultural commonwealth*, *Regional realm* (C212–C214).
- **0.10.7:** `[V-GAME]` the New World's countries are dimmed in the lobby list instead of hidden, which ends the list's flicker (C205–C211).
- **0.10.6:** `[V-GAME]` fixes from the first console sitting on EU5 1.4.4 (C198–C204).
- **0.10.5:** content model and first stories: *River centre*, *Sacred centre* and the *River-basin union* formable (C193–C196).
- **0.10.4:** five rare resource places replace the vanished historical bonuses: silver, a mercury lode, rich fisheries (C189–C190).
- **0.10.3:** N0 decisions carried out. American historical events, colonial names, colonial formables and the Panama canal are gated off on generated land, and historical formables take the places of their culture (C187–C188).
- **0.10.2:** the mod's languages are taken from the installation; all eleven official languages are written, including Turkish (C178, C186).
- **0.10.0 – 0.10.1:** the country-selection cover uses vanilla terra incognita drawings (C172–C174).

## 0.9.24 – 0.9.33 — 2026-10-22 to 2026-10-23

- **0.9.33:** holders of the great empires' opinions discover their partners' capitals (C170–C171).
- **0.9.32:** the country-selection cover stays on the map and off the frame (C169).
- **0.9.30 – 0.9.31:** the spline network: road strips for generated locations, in vanilla's order. `[V-GAME]` no strip errors, and roads are drawn (C161–C168; [interoperability register](docs/research/interoperability.md) R-001).
- **0.9.29:** great empires with vanilla ranks, royal roads, feared neighbours and resentful vassals (R7c, C160).
- **0.9.28:** technology levels and regional families from each society (R7b, C159).
- **0.9.26 – 0.9.27:** extended New World cover and lobby guards. The cover is isolated in a private map-mesh include so loading screens and character scenes keep vanilla shaders (C150–C154).
- **0.9.25:** verified against EU5 1.4.3 (Steam build 26105915) (C148–C149).
- **0.9.24:** reproducible layered worlds and the independent generator application: world codes, library, rerolls, world files, queue, atlas ([ADR 0010](docs/adr/0010-layered-worlds-and-a-generator-of-its-own.md), C141–C147).

## 0.9.1 – 0.9.14 — 2026-10-19 to 2026-10-21

- **0.9.14:** every world is a mod of its own. Adds world types, playable settings ranges and spoiler-free pictures (C116–C120).
- Delivery decided: one Workshop item carries the generator, and worlds are built locally ([ADR 0009](docs/adr/0009-hub-mod-with-generator.md)). The project is licensed under MPL-2.0.
- Rust core for the hot kernels ([ADR 0005](docs/adr/0005-native-core.md)), machine-aware threads and memory ([ADR 0006](docs/adr/0006-machine-resources.md)), and the Qt application window ([ADR 0007](docs/adr/0007-application-window-and-packaging.md)).
- **0.9.6 – 0.9.13:** EU5 1.4.2 support, collision-free localisation keys, government templates, and fixes found against the vanilla 1.4.2 baseline log.
- **0.9.4 – 0.9.5:** compact, connected areas and regions; coastal water belongs to the region of its shore.
- **0.9.2 – 0.9.3:** start development, harbours and market villages from the societies (R7a, C73–C76).
- **0.9.1:** one product version for the mod and its output (ADR 0003).

## Earlier development — 2026-10-13 to 2026-10-19

- **R6 (generator 0.8.0 – 0.9.0):** native societies (hearths, cultures, religions, states, tribes, towns, markets, holy sites), place names in local languages, and vassals. `[V-GAME]` loads with visible states (C67–C72).
- **V1 (generator 0.4.0 – 0.7.0):** terrain from one relief, climate and biome model, rivers from drainage, and coastlines that follow the seed. `[V-GAME]` accepted by the owner (C47–C66).
- **T3 (2026-10-14 – 15):** a New World with new location IDs replaces the 1337 Americas, and its terrain decals, water, foam and lake meshes are rebuilt. `[V-GAME]` the first playable start (C42–C46).
- **D0 (2026-10-14):** the first deterministic geography generator: moved land–sea boundaries between existing American location IDs, byte-reproducible. `[V-GAME]` location outlines follow the mod's raster (C28–C34).
- **Research (2026-10-13):** inventory of EU5 1.4.1, the map contract and its fingerprint, the feasibility ladder, and a metadata-only test mod (C01–C27).
