# Copyright © 2026 Draconov
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

# Gradient preset metadata transcribed from the user-provided saved DitherEffect page.
# RasterMint uses its own gradient interpolation implementation; no external code is copied.
GRADIENT_PRESETS: tuple[dict[str, object], ...] = (
    {
        "name": 'Tideway Static',
        "colors": ('#848677', '#FA5E68', '#0099FF', '#848677', '#8C9488'),
        "positions": (0.0, 0.167, 0.3919, 0.5955, 1.0),
    },
    {
        "name": 'Caustic Fog',
        "colors": ('#88847B', '#0590FF', '#DCFF00', '#88847B', '#010100'),
        "positions": (0.0, 0.2837, 0.3091, 0.5845, 1.0),
    },
    {
        "name": 'Polar Ink',
        "colors": ('#0C1118', '#081C35', '#AFE0DB'),
        "positions": (0.0, 0.3589, 0.991),
    },
    {
        "name": 'Ultramarine Dust',
        "colors": ('#0A08FB', '#887978'),
        "positions": (0.0, 0.594),
    },
    {
        "name": 'Blue Steel',
        "colors": ('#0900FC', '#ABB2AB', '#7E7D79'),
        "positions": (0.0, 0.2876, 0.594),
    },
    {
        "name": 'Afterglint',
        "colors": ('#411928', '#B19490', '#22C8D0', '#F0C4F7'),
        "positions": (0.2209, 0.4094, 0.7158, 1.0),
    },
    {
        "name": 'Ultramarine Blackout',
        "colors": ('#0B07FF', '#79797F', '#000000'),
        "positions": (0.0, 0.604, 1.0),
    },
    {
        "name": 'Alloy Afterglow',
        "colors": ('#3C1B31', '#988ACE', '#24CAD1', '#C3C0C1'),
        "positions": (0.2209, 0.3975, 0.5376, 0.6731),
    },
    {
        "name": 'Brackish Signal',
        "colors": ('#7B8088', '#068FFD', '#7B8088', '#000100'),
        "positions": (0.0, 0.2437, 0.5445, 1.0),
    },
    {
        "name": 'Jade Pulsewine',
        "colors": ('#451631', '#00FF79', '#2DCDC3', '#CAB9C6'),
        "positions": (0.2209, 0.3875, 0.5276, 0.6731),
    },
    {
        "name": 'Periwave',
        "colors": ('#9BDEDF', '#E5D5F4', '#9780F3'),
        "positions": (0.0, 0.52, 1.0),
    },
    {
        "name": 'Fallow',
        "colors": ('#6F683C', '#C7F98A', '#FFF9F7'),
        "positions": (0.1255, 0.3794, 1.0),
    },
    {
        "name": 'Tidal Flare',
        "colors": ('#FF5007', '#0572FF', '#B7BEAF'),
        "positions": (0.0, 0.3538, 1.0),
    },
    {
        "name": 'Polar Rupture',
        "colors": ('#00F2FF', '#FDFFFF', '#00EBF5', '#050806', '#050806'),
        "positions": (0.0, 0.2168, 0.4483, 0.5315, 1.0),
    },
    {
        "name": 'Plum Brazier',
        "colors": ('#8C3C80', '#B25C00', '#987A6B'),
        "positions": (0.1685, 0.5052, 0.8699),
    },
    {
        "name": 'Cyan Bulkhead',
        "colors": ('#C4BEC4', '#0086FB', '#575055', '#000800', '#0086FB'),
        "positions": (0.0, 0.1658, 0.4497, 0.7392, 1.0),
    },
    {
        "name": 'Glacial Descent',
        "colors": ('#F6F9F5', '#81F0FF', '#5B9CC0', '#4D66A2', '#0A0005'),
        "positions": (0.0, 0.1421, 0.3984, 0.5725, 1.0),
    },
    {
        "name": 'Snowburn',
        "colors": ('#FDF9FF', '#F81800', '#060201', '#060201'),
        "positions": (0.0, 0.5911, 0.687, 1.0),
    },
    {
        "name": 'Magenta Dropoff',
        "colors": ('#8A7E86', '#FF00AD', '#000000'),
        "positions": (0.0, 0.4477, 1.0),
    },
    {
        "name": 'Amethyst Fault',
        "colors": ('#817F8E', '#9C07FE', '#000000', '#000000'),
        "positions": (0.0, 0.6475, 0.6521, 1.0),
    },
    {
        "name": 'Fuchsia Soot',
        "colors": ('#F65BA2', '#3B4340', '#747A79'),
        "positions": (0.0, 0.7397, 1.0),
    },
    {
        "name": 'Amber Quench',
        "colors": ('#A3A1AF', '#FF9600', '#030300'),
        "positions": (0.0, 0.6692, 0.7976),
    },
    {
        "name": 'Crossfire',
        "colors": ('#031125', '#1F35FF', '#FF050A'),
        "positions": (0.0625, 0.4856, 0.8406),
    },
    {
        "name": 'Apogee',
        "colors": ('#000419', '#B320A8', '#5372DB'),
        "positions": (0.0, 0.5979, 0.981),
    },
    {
        "name": 'Voltage Midway',
        "colors": ('#4D4846', '#006DFF', '#000001', '#703CCE', '#725DFF', '#999DFF', '#575F8F', '#FF0201', '#FFD808'),
        "positions": (0.0, 0.095, 0.1702, 0.3804, 0.5022, 0.5617, 0.7619, 0.8657, 1.0),
    },
    {
        "name": 'Concrete Rose',
        "colors": ('#817E84', '#FFA0C1', '#B7B9C1'),
        "positions": (0.1121, 0.3537, 0.5984),
    },
    {
        "name": 'Lattice Equinox',
        "colors": ('#FACC00', '#89CB2D', '#00000A', '#705CFF', '#00000A', '#705CFF', '#F6C500', '#89CB2D'),
        "positions": (0.0, 0.2322, 0.2901, 0.4822, 0.6963, 0.8764, 0.9048, 1.0),
    },
    {
        "name": 'Frosted Switchboard',
        "colors": ('#F7F6FF', '#056AF6', '#6F34CC', '#000000', '#6868FF', '#000000', '#6868FF', '#FF008D', '#363864'),
        "positions": (0.0, 0.1453, 0.2822, 0.3301, 0.4585, 0.6289, 0.8501, 0.9184, 1.0),
    },
    {
        "name": 'Abyssal Estuary',
        "colors": ('#050100', '#3E7D74', '#09C9FF', '#3E7D74', '#050100', '#988F97', '#050100'),
        "positions": (0.0, 0.3425, 0.5346, 0.6948, 0.8318, 0.9565, 1.0),
    },
    {
        "name": 'Seizurecore',
        "colors": ('#FFFAFF', '#0063FF', '#000302', '#6E3BC4', '#6668FF', '#F5078E', '#000302', '#FF0700', '#FFD407'),
        "positions": (0.0, 0.1921, 0.3296, 0.4499, 0.5127, 0.6511, 0.7378, 0.9157, 0.9536),
    },
    {
        "name": 'Fusepoint',
        "colors": ('#02B4F5', '#0A0103', '#273D37', '#02B4F5', '#FF3100'),
        "positions": (0.0, 0.0933, 0.769, 0.8147, 0.8857),
    },
    {
        "name": 'Chroma Fracture',
        "colors": ('#FB00A2', '#070000', '#696DFF', '#070000', '#696DFF', '#FF0A86'),
        "positions": (0.0, 0.3101, 0.5222, 0.6963, 0.8664, 0.897),
    },
    {
        "name": 'Bathyal',
        "colors": ('#000D24', '#616B93'),
        "positions": (0.3789, 0.9783),
    },
    {
        "name": 'Synthwave',
        "colors": ('#00021E', '#0E41B8', '#FC2466'),
        "positions": (0.083, 0.4299, 0.8406),
    },
    {
        "name": 'Lavender Fault',
        "colors": ('#C0AEBD', '#BE7BFF', '#FD4903', '#CCCFC9'),
        "positions": (0.0, 0.4284, 0.4961, 1.0),
    },
    {
        "name": 'Sunset Parfait',
        "colors": ('#CDE9EE', '#FF81CD', '#FA6600', '#AFAFA0'),
        "positions": (0.0, 0.6333, 0.6436, 1.0),
    },
    {
        "name": 'Taffeta',
        "colors": ('#FF77BA', '#CF6634', '#7987B7', '#D5C4A6'),
        "positions": (0.0259, 0.2925, 0.7348, 1.0),
    },
    {
        "name": 'Apricot Weather',
        "colors": ('#F8D1A6', '#F0975E', '#C8556B', '#EAE1C2'),
        "positions": (0.0259, 0.2725, 0.7148, 1.0),
    },
    {
        "name": 'Citrine',
        "colors": ('#FFE245', '#F7889E', '#FBEBC0', '#B4CC90'),
        "positions": (0.0259, 0.414, 0.7248, 1.0),
    },
    {
        "name": 'Candy Furnace',
        "colors": ('#FFBC3A', '#FF9236', '#F55BB3', '#DD8CD8', '#FFC7EA'),
        "positions": (0.0259, 0.2187, 0.4533, 0.6948, 1.0),
    },
    {
        "name": 'Daydream',
        "colors": ('#E7E99E', '#B2CAD0', '#E888B0', '#FCF8BE'),
        "positions": (0.0259, 0.4333, 0.7348, 1.0),
    },
    {
        "name": 'Sorbet',
        "colors": ('#FF889B', '#F7D494', '#FFD398', '#CDE1FD'),
        "positions": (0.0259, 0.4333, 0.7148, 1.0),
    },
    {
        "name": 'Verdant Prism',
        "colors": ('#61E196', '#2DAEFA', '#517CFF', '#2DAEFA', '#ECC1FF'),
        "positions": (0.0085, 0.2881, 0.5449, 0.7244, 1.0),
    },
    {
        "name": 'Papaya Whisper',
        "colors": ('#FF8B47', '#F56689', '#FBA77D', '#FEF8F0'),
        "positions": (0.0259, 0.4133, 0.7348, 1.0),
    },
    {
        "name": 'Tropic Downpour',
        "colors": ('#FD6F6E', '#EAD962', '#5BC78D', '#30A2C3', '#FCFFFF'),
        "positions": (0.0085, 0.2781, 0.4849, 0.7344, 1.0),
    },
    {
        "name": 'Midnight Peony',
        "colors": ('#060821', '#642F47', '#FBF0FA'),
        "positions": (0.0, 0.822, 1.0),
    },
    {
        "name": 'Sugared Wisteria',
        "colors": ('#C8A5F1', '#F9ACF5', '#FFFDD1', '#BB9DFF'),
        "positions": (0.0, 0.3672, 0.6602, 1.0),
    },
    {
        "name": 'Verdigris Loam',
        "colors": ('#73BD76', '#E7C381', '#CC7E65', '#654F58'),
        "positions": (0.0, 0.3716, 0.7517, 1.0),
    },
    {
        "name": 'Rougelace',
        "colors": ('#F41210', '#F58AAF', '#FFEAF0', '#BDBDFB'),
        "positions": (0.0234, 0.4033, 0.8608, 1.0),
    },
    {
        "name": 'Plum Current',
        "colors": ('#62409F', '#DB356B', '#E5AF9D', '#4C6BAD'),
        "positions": (0.0, 0.2778, 0.7842, 1.0),
    },
    {
        "name": 'Blush Kindling',
        "colors": ('#FFB4D1', '#F7601D', '#FF8B4F', '#F20C59', '#940F66'),
        "positions": (0.0, 0.2336, 0.5298, 0.7639, 1.0),
    },
    {
        "name": 'Seaglass Parchment',
        "colors": ('#ABEBF5', '#94DDEA', '#779CC6', '#F9F1D8'),
        "positions": (0.0259, 0.3176, 0.7122, 1.0),
    },
    {
        "name": 'Kaleidoscope',
        "colors": ('#FDBAB0', '#E8F785', '#B3FBE2', '#A3A3F0', '#D4A9FD', '#93C2C2'),
        "positions": (0.0, 0.199, 0.3891, 0.5942, 0.8264, 1.0),
    },
    {
        "name": 'Sunshower',
        "colors": ('#FA1400', '#E8EA9B', '#92C2DF'),
        "positions": (0.0085, 0.7202, 1.0),
    },
    {
        "name": 'Slate Resonance',
        "colors": ('#9594AD', '#504EA9', '#363D78', '#504EA9', '#9594AD'),
        "positions": (0.0, 0.4089, 0.69, 0.8552, 1.0),
    },
    {
        "name": 'Sherbet Riptide',
        "colors": ('#F6724B', '#F295CF', '#B7EEFF', '#FFB7BF'),
        "positions": (0.0085, 0.2874, 0.6802, 1.0),
    },
    {
        "name": 'Saffron Bruise',
        "colors": ('#F5E69B', '#DE717D', '#7B4DAC', '#689BA8', '#24182A'),
        "positions": (0.0, 0.2036, 0.5398, 0.7737, 1.0),
    },
    {
        "name": 'Seafoam Veil',
        "colors": ('#FFB7C3', '#CEA6FA', '#8BCCC6', '#FDFFFF'),
        "positions": (0.0085, 0.3374, 0.6602, 1.0),
    },
    {
        "name": 'Crushed Terracotta',
        "colors": ('#F1392A', '#BA93C9', '#E7D5CC'),
        "positions": (0.0, 0.4751, 1.0),
    },
    {
        "name": 'Opaline',
        "colors": ('#E09DA3', '#BBC8BE', '#64C6DF', '#B39EDD', '#77C4D9'),
        "positions": (0.0, 0.22, 0.48, 0.72, 1.0),
    },
    {
        "name": 'Estuary Lichen',
        "colors": ('#152422', '#485B71', '#A4C399', '#8B9EB2'),
        "positions": (0.0, 0.3665, 0.7146, 1.0),
    },
    {
        "name": 'Confection Dawn',
        "colors": ('#E8D1F9', '#FAA7C2', '#F4EAAE', '#D8D8F3'),
        "positions": (0.0, 0.3123, 0.6609, 1.0),
    },
    {
        "name": 'Afterimage Eclipse',
        "colors": ('#FBFA00', '#FFFFFF', '#FFFA09', '#4C4A4D', '#000000'),
        "positions": (0.0, 0.156, 0.4907, 0.6145, 1.0),
    },
    {
        "name": 'Coalflare',
        "colors": ('#020812', '#091A41', '#B32300'),
        "positions": (0.0, 0.4089, 1.0),
    },
    {
        "name": 'Crystal Visions',
        "colors": ('#4934B4', '#95AFF1', '#B9D26E', '#BC74D9', '#FCF8D7'),
        "positions": (0.0, 0.2378, 0.4575, 0.6806, 1.0),
    },
    {
        "name": 'Cinder Torch',
        "colors": ('#1C1B17', '#164050', '#FE8131', '#E41322', '#150C1A'),
        "positions": (0.0, 0.207, 0.4673, 0.7403, 1.0),
    },
    {
        "name": 'Aether Pulse',
        "colors": ('#020002', '#3403D8', '#0126C3', '#C69BF5'),
        "positions": (0.0, 0.383, 0.7527, 1.0),
    },
    {
        "name": 'Lavender Channel',
        "colors": ('#7843F7', '#5B6DFF', '#CE7CF6', '#B3B8D3'),
        "positions": (0.0, 0.383, 0.6927, 1.0),
    },
    {
        "name": 'Nocturne Chlorophyll',
        "colors": ('#0C0010', '#8207F1', '#7DA9E3', '#1FF303', '#7DA9E3'),
        "positions": (0.0, 0.2092, 0.4289, 0.6255, 1.0),
    },
    {
        "name": 'Chromatic Ambush',
        "colors": ('#000000', '#2610DB', '#0025BC', '#E00F14', '#F96600', '#D092F4'),
        "positions": (0.0, 0.1992, 0.3789, 0.6055, 0.7898, 1.0),
    },
    {
        "name": 'Verdance',
        "colors": ('#050203', '#206F06', '#4EE210', '#BEF6A7', '#FFEC00'),
        "positions": (0.0, 0.2793, 0.6421, 0.7839, 0.9941),
    },
    {
        "name": 'Blood Camellia',
        "colors": ('#080E1A', '#932428', '#F37881', '#E92022'),
        "positions": (0.0, 0.3389, 0.627, 1.0),
    },
    {
        "name": 'Prism Singularity',
        "colors": ('#020509', '#F10767', '#F4F814', '#0DFDD5', '#5000F5', '#020509'),
        "positions": (0.0, 0.2302, 0.4336, 0.5545, 0.8308, 1.0),
    },
    {
        "name": 'Brimstone Sky',
        "colors": ('#2B2617', '#E52F4B', '#F1A852', '#3260BF', '#E0CDC5'),
        "positions": (0.0, 0.3122, 0.4973, 0.7197, 1.0),
    },
    {
        "name": 'Magenta Scone',
        "colors": ('#FA6971', '#7805FB', '#2F0053'),
        "positions": (0.0, 0.4895, 1.0),
    },
    {
        "name": 'Dusky Carousel',
        "colors": ('#00060A', '#608FBE', '#E161E6', '#D67234', '#E1DCDF'),
        "positions": (0.0, 0.2722, 0.5073, 0.7397, 1.0),
    },
    {
        "name": 'Crimson Undertide',
        "colors": ('#F66465', '#001E29', '#7B00F5', '#001E29', '#33034B'),
        "positions": (0.0, 0.2099, 0.4495, 0.8706, 1.0),
    },
    {
        "name": 'Prismatica',
        "colors": ('#203D65', '#FC00F5', '#FB6900', '#F6D48C', '#77D0FF', '#B056FF'),
        "positions": (0.0, 0.1675, 0.3779, 0.5684, 0.7879, 1.0),
    },
    {
        "name": 'Porcelain Halo',
        "colors": ('#FFF6FE', '#9187FD', '#FE7CC8', '#FFF6FE'),
        "positions": (0.0, 0.5574, 0.7654, 1.0),
    },
    {
        "name": 'Dockyard Heat',
        "colors": ('#202230', '#2F86E5', '#7B4E57', '#FB6359', '#FFEFA9', '#E1DDD6'),
        "positions": (0.0, 0.1621, 0.3765, 0.5879, 0.8169, 1.0),
    },
    {
        "name": 'Scoria Bloom',
        "colors": ('#8D9096', '#CF88F9', '#F95700'),
        "positions": (0.0, 0.4826, 1.0),
    },
    {
        "name": 'Ashring Lumen',
        "colors": ('#B1B4B4', '#A7D3FF', '#040008', '#FF53D4', '#B1B4B4'),
        "positions": (0.0, 0.2419, 0.4937, 0.8008, 1.0),
    },
    {
        "name": 'Cobalt Monolith',
        "colors": ('#000000', '#0077FF', '#79756F'),
        "positions": (0.1731, 0.5334, 1.0),
    },
    {
        "name": 'Kindle',
        "colors": ('#1B0A08', '#EE5950', '#EED5C3'),
        "positions": (0.0, 0.3955, 1.0),
    },
    {
        "name": 'Static Midway',
        "colors": ('#92918D', '#FF28B8', '#060208', '#FF28B8', '#92918D', '#FFC995', '#FF28B8', '#F64E00'),
        "positions": (0.0, 0.073, 0.1931, 0.4726, 0.5613, 0.6921, 0.8808, 1.0),
    },
    {
        "name": 'Saffron Ashveil',
        "colors": ('#B7B1BD', '#000504', '#F8E04C', '#B7B1BD'),
        "positions": (0.0, 0.6734, 0.8237, 1.0),
    },
    {
        "name": 'Arcade Pollinator',
        "colors": ('#401B52', '#FF00F9', '#96B1FE', '#BBFF06', '#F900AA'),
        "positions": (0.2637, 0.4783, 0.6045, 0.8469, 1.0),
    },
    {
        "name": 'Mosswine Surge',
        "colors": ('#B8E4DF', '#1D6EE3', '#5CE18D', '#9B2F4E', '#1F2B1B'),
        "positions": (0.0, 0.2302, 0.4778, 0.6665, 1.0),
    },
    {
        "name": 'Cobalt Citrine',
        "colors": ('#474F44', '#037AFF', '#E986FF', '#FF7A39'),
        "positions": (0.0, 0.3332, 0.636, 1.0),
    },
    {
        "name": 'Arcflash Plate',
        "colors": ('#BABABD', '#000000', '#5F7CFF', '#BABABD'),
        "positions": (0.0, 0.6634, 0.8137, 1.0),
    },
    {
        "name": 'Vesper',
        "colors": ('#FFF5F6', '#8B7EFF', '#FF7BB5', '#02000A'),
        "positions": (0.0, 0.5733, 0.6536, 1.0),
    },
    {
        "name": 'Traffic Lichen',
        "colors": ('#9CA0A4', '#FF6700', '#D2E700', '#B5ABA7'),
        "positions": (0.0, 0.3464, 0.7068, 1.0),
    },
    {
        "name": 'Skyway Patina',
        "colors": ('#0C1416', '#163490', '#4D79E7', '#5FB6F6', '#B5CDF5'),
        "positions": (0.0, 0.1717, 0.5237, 0.677, 1.0),
    },
    {
        "name": 'Lime Cindersmoke',
        "colors": ('#AAFC64', '#3D3E3B', '#757D79'),
        "positions": (0.0, 0.7097, 1.0),
    },
    {
        "name": 'Voidfire Glacier',
        "colors": ('#000006', '#FF6878', '#99B4FF', '#FB9800'),
        "positions": (0.2637, 0.4483, 0.6245, 0.8066),
    },
    {
        "name": 'Taffy',
        "colors": ('#DAD0CC', '#FF5D65', '#F99343', '#C162FF', '#B5A6AB'),
        "positions": (0.0, 0.3464, 0.4778, 0.6712, 1.0),
    },
    {
        "name": 'Rustbelt',
        "colors": ('#292D1E', '#D92914', '#D7A17C', '#D2D5CD'),
        "positions": (0.0, 0.3555, 0.6902, 1.0),
    },
    {
        "name": 'Lilac Burnout',
        "colors": ('#AFABF6', '#FD5700', '#9FA6AE', '#050003'),
        "positions": (0.0, 0.3442, 0.664, 1.0),
    },
    {
        "name": 'Beacon Undertow',
        "colors": ('#A7FBFF', '#FC0001', '#2B79E4', '#08272E'),
        "positions": (0.0, 0.3242, 0.7414, 0.9424),
    },
    {
        "name": 'Crimson Switchyard',
        "colors": ('#4F4048', '#050700', '#FF7777', '#98B9FF', '#B0E5FF', '#FF9C01', '#D7007D', '#7D0045'),
        "positions": (0.0554, 0.2937, 0.4483, 0.6645, 0.6655, 0.7766, 0.9316, 1.0),
    },
    {
        "name": 'Tidemark',
        "colors": ('#2DA9C9', '#331D29', '#2DA9C9', '#B8B6B1'),
        "positions": (0.0, 0.2608, 0.5476, 0.6731),
    },
    {
        "name": 'Headland',
        "colors": ('#293154', '#396792', '#FF655E', '#C8C6CB'),
        "positions": (0.0, 0.4497, 0.6379, 0.7908),
    },
    {
        "name": 'Mosaic Switchyard',
        "colors": ('#897578', '#532930', '#0496FF', '#A99B9C', '#593344', '#0095FC', '#213823', '#AFB6B7'),
        "positions": (0.0, 0.0784, 0.2437, 0.5301, 0.7414, 0.8491, 0.9019, 1.0),
    },
    {
        "name": 'Chromatic Relic',
        "colors": ('#98FFF9', '#B59D49', '#FD0004', '#D73988', '#B59D49', '#09192F', '#F208F8'),
        "positions": (0.0, 0.1396, 0.2629, 0.445, 0.5515, 0.7812, 1.0),
    },
    {
        "name": 'Paradox',
        "colors": ('#080300', '#82693D', '#5F192D', '#FFD300', '#05A4F9', '#4A517A', '#5F192D', '#C86B33', '#080300'),
        "positions": (0.0, 0.0816, 0.1604, 0.4939, 0.4949, 0.7532, 0.864, 0.905, 1.0),
    },
    {
        "name": 'Halation Loop',
        "colors": ('#C3C0CE', '#3167CD', '#DC03F6', '#FF5BA2', '#C3C0CE'),
        "positions": (0.0, 0.1204, 0.3421, 0.5662, 1.0),
    },
    {
        "name": 'Citrus Glint',
        "colors": ('#B2B9B8', '#F75A16', '#FDAD04', '#FBFBFF'),
        "positions": (0.0, 0.4975, 0.7554, 1.0),
    },
    {
        "name": 'Cindercone',
        "colors": ('#FFD203', '#FF6204', '#A1A1A6'),
        "positions": (0.0, 0.3142, 0.655),
    },
    {
        "name": 'Amethyst Honeydrop',
        "colors": ('#5909E0', '#B439FF', '#F66DDD', '#F5AB26', '#FFE1C0'),
        "positions": (0.0, 0.2197, 0.5002, 0.7431, 1.0),
    },
    {
        "name": 'Pulse Interference',
        "colors": ('#B9B6B3', '#040000', '#A2C6F6', '#040000', '#F65DD3', '#040000', '#B9B6B3'),
        "positions": (0.0, 0.1284, 0.2519, 0.5337, 0.8008, 0.8626, 1.0),
    },
    {
        "name": 'Blood Semaphore',
        "colors": ('#0A0000', '#FF0300', '#5C2323', '#3F7171', '#FF0300', '#3F7171', '#0A0000', '#FF0300', '#0A0000'),
        "positions": (0.0, 0.0935, 0.1704, 0.3391, 0.607, 0.7354, 0.8577, 0.9904, 1.0),
    },
    {
        "name": 'Sunblind',
        "colors": ('#BBB6B9', '#FFD4A2', '#133621', '#FA470E', '#FFB508', '#133621', '#FAFFFF'),
        "positions": (0.0, 0.0857, 0.2463, 0.4775, 0.7254, 0.927, 1.0),
    },
    {
        "name": 'Chimera',
        "colors": ('#302D13', '#4C3D5D', '#469ABE', '#8B9930', '#BB9907', '#FB353C'),
        "positions": (0.0, 0.2527, 0.426, 0.5335, 0.7978, 1.0),
    },
    {
        "name": 'Tempest Weave',
        "colors": ('#000800', '#642B26', '#34786E', '#086BFF', '#225653', '#642B26', '#086BFF', '#000800'),
        "positions": (0.0, 0.1804, 0.3855, 0.5967, 0.7532, 0.864, 0.905, 1.0),
    },
    {
        "name": 'Fuchsia Ash',
        "colors": ('#FB00C4', '#A5A4A8', '#030008', '#030008', '#F83BC5'),
        "positions": (0.0, 0.1768, 0.5415, 0.8408, 1.0),
    },
    {
        "name": 'Signal Breaker',
        "colors": ('#02A7F6', '#000806', '#FF310A', '#20373D', '#02A7F6', '#000806'),
        "positions": (0.0, 0.0933, 0.5378, 0.749, 0.8447, 0.8586),
    },
    {
        "name": 'Cinderpetal',
        "colors": ('#FF6CB6', '#381821', '#CD1E48', '#BBAFB5'),
        "positions": (0.0, 0.2608, 0.5476, 0.6731),
    },
    {
        "name": 'Warmed Fuse',
        "colors": ('#95A1A5', '#332223', '#9CAAA8', '#D82781', '#FF8104'),
        "positions": (0.0, 0.2109, 0.3535, 0.7058, 1.0),
    },
    {
        "name": 'Cryo Reentry',
        "colors": ('#9FF6FC', '#031C29', '#FF6122', '#F947A7', '#031C29', '#9FF6FC'),
        "positions": (0.0, 0.0664, 0.2329, 0.3492, 0.7766, 1.0),
    },
    {
        "name": 'Tokyo Midnight',
        "colors": ('#F5FFFF', '#0072F5', '#000000', '#762FCC', '#7263FC', '#FF0A98', '#000000', '#353565'),
        "positions": (0.0, 0.1553, 0.3401, 0.396, 0.4766, 0.6489, 0.8276, 1.0),
    },
    {
        "name": 'Scald',
        "colors": ('#7C827F', '#FB0000', '#080307', '#080307'),
        "positions": (0.0, 0.6575, 0.6621, 1.0),
    },
    {
        "name": 'Coral Dropoff',
        "colors": ('#A1F4FF', '#FF712A', '#F74CA3', '#072833'),
        "positions": (0.0, 0.2229, 0.3492, 0.8142),
    },
    {
        "name": 'Neon Rhodium',
        "colors": ('#D09BFF', '#051834', '#051834', '#FF04A5'),
        "positions": (0.0623, 0.3296, 0.6875, 1.0),
    },
    {
        "name": 'Chrome Orchard',
        "colors": ('#99C1F5', '#FF0099', '#020000', '#99C1F5', '#FF0099', '#0A56F5', '#020000', '#829084'),
        "positions": (0.0, 0.0843, 0.2837, 0.5906, 0.7781, 0.7791, 0.9094, 1.0),
    },
    {
        "name": 'Molten Splice',
        "colors": ('#A19FA8', '#FF5400', '#FB0007', '#FB00A8', '#A19FA8'),
        "positions": (0.0, 0.3826, 0.4834, 0.6489, 0.8428),
    },
    {
        "name": 'Smolder',
        "colors": ('#060800', '#9C392E', '#FFE6B8'),
        "positions": (0.0, 0.7251, 0.9861),
    },
    {
        "name": 'Coral Siren',
        "colors": ('#A4FFFF', '#FF0104', '#DD3083', '#001F23'),
        "positions": (0.0, 0.2229, 0.3592, 0.8142),
    },
    {
        "name": 'Powdered Twilight',
        "colors": ('#E1F9FF', '#C4BDC8', '#AA9EC4', '#8F8BB6', '#D26EB8'),
        "positions": (0.0, 0.26, 0.4788, 0.77, 1.0),
    },
    {
        "name": 'Kiln Vermilion',
        "colors": ('#401622', '#F50300', '#DA5C21', '#C1C1B3'),
        "positions": (0.2209, 0.4275, 0.5676, 0.6731),
    },
    {
        "name": 'Reefburn Garnet',
        "colors": ('#000B13', '#D7157C', '#E3785C'),
        "positions": (0.0, 0.3254, 0.981),
    },
    {
        "name": 'Poppy Ironwash',
        "colors": ('#B84D1F', '#F6017F', '#B3BABC'),
        "positions": (0.0, 0.3738, 1.0),
    },
    {
        "name": 'Heirloom',
        "colors": ('#8E74AF', '#E6E4B7', '#89A7C9'),
        "positions": (0.0085, 0.6582, 0.9888),
    },
    {
        "name": 'Indigo Meltwater',
        "colors": ('#081E25', '#4A46D2', '#CDDFFF'),
        "positions": (0.0085, 0.2552, 0.9888),
    },
    {
        "name": 'Petal Thaw',
        "colors": ('#BBEDF8', '#E3ADC6', '#E65E8E', '#ECF8E0'),
        "positions": (0.0, 0.3123, 0.6009, 1.0),
    },
    {
        "name": 'Apricot Hearthlight',
        "colors": ('#E73141', '#FE881C', '#FDC93C', '#FFF5EA', '#ECB19F'),
        "positions": (0.0, 0.2161, 0.3687, 0.5984, 1.0),
    },
    {
        "name": 'Carnelian Turnstile',
        "colors": ('#15190C', '#8B72AA', '#EE6FB6', '#E09C29', '#E62734', '#9D8AB5'),
        "positions": (0.0, 0.2378, 0.4075, 0.5739, 0.6906, 1.0),
    },
    {
        "name": 'Amber Dunelight',
        "colors": ('#0A161E', '#EBB34E', '#EEDBC3'),
        "positions": (0.0, 0.4907, 1.0),
    },
    {
        "name": 'Copper Bloomcast',
        "colors": ('#221622', '#D5395D', '#EF7D38', '#DFD1B7'),
        "positions": (0.0, 0.3306, 0.5779, 1.0),
    },
    {
        "name": 'Sleeping Perriwinkle',
        "colors": ('#010000', '#0D1FDE', '#D96BE3', '#E3D8DD'),
        "positions": (0.0, 0.3069, 0.6902, 1.0),
    },
    {
        "name": 'Abyssal Beacon',
        "colors": ('#000F29', '#3125EA', '#34A3EE', '#EAF7FC'),
        "positions": (0.0, 0.2002, 0.4578, 1.0),
    },
    {
        "name": 'Foundry Harvest',
        "colors": ('#28101E', '#3B2525', '#916529', '#FFD027', '#6D7D75', '#BDC9CC'),
        "positions": (0.0, 0.198, 0.3094, 0.5359, 0.8308, 0.99),
    },
    {
        "name": 'Electrum Mirage',
        "colors": ('#000000', '#460629', '#B600A4', '#1691E3', '#DF31AC', '#EEEDF6'),
        "positions": (0.0, 0.1736, 0.3616, 0.5884, 0.8235, 1.0),
    },
    {
        "name": 'Barley Vector',
        "colors": ('#212817', '#304988', '#CF8D54', '#B5C572', '#D7DEC0'),
        "positions": (0.0, 0.2302, 0.4978, 0.7065, 1.0),
    },
    {
        "name": 'Oxide Breaker',
        "colors": ('#420015', '#B31631', '#F9933A', '#7F786E', '#C4D4CD'),
        "positions": (0.0, 0.2659, 0.5149, 0.8383, 1.0),
    },
    {
        "name": 'Overcast Estuary',
        "colors": ('#091309', '#333238', '#6996C0', '#CCE3DE', '#E8E9FF', '#7D8374'),
        "positions": (0.0, 0.2112, 0.3984, 0.6064, 0.7954, 1.0),
    },
    {
        "name": 'Orchard Voltage',
        "colors": ('#1E2E24', '#7B0FE4', '#EA7D29', '#ADDACD'),
        "positions": (0.0, 0.3279, 0.6931, 1.0),
    },
    {
        "name": 'Aurora Spillway',
        "colors": ('#090B1A', '#6D42B2', '#F4A1FF', '#0D8AE4', '#0FFEFF', '#ECD7E5'),
        "positions": (0.0, 0.2236, 0.4211, 0.5745, 0.7878, 1.0),
    },
    {
        "name": 'Brineglass Noon',
        "colors": ('#010200', '#181D29', '#1CBCDB', '#FBDB0D', '#F26B14', '#1F2116'),
        "positions": (0.0, 0.1712, 0.5073, 0.655, 0.8313, 1.0),
    },
    {
        "name": 'Verdant Interlude',
        "colors": ('#0D1929', '#023A12', '#3E8417', '#FECFD3', '#3E8417', '#0D1929'),
        "positions": (0.0, 0.1997, 0.3779, 0.5093, 0.7593, 1.0),
    },
    {
        "name": 'Cinder Meadowrun',
        "colors": ('#2C1F30', '#D72B41', '#F84C0F', '#84FF24', '#C5CBAE'),
        "positions": (0.0, 0.1936, 0.3711, 0.7712, 1.0),
    },
    {
        "name": 'Plasma Shockwave',
        "colors": ('#000000', '#5A35C3', '#FF0FBA', '#1DFCFB', '#DEF99D'),
        "positions": (0.0, 0.165, 0.4165, 0.7283, 1.0),
    },
    {
        "name": 'Dusk Reliquary',
        "colors": ('#060107', '#1E205F', '#7C7DDB', '#F9E5ED', '#A68444', '#00000B'),
        "positions": (0.0, 0.2283, 0.3616, 0.565, 0.7873, 1.0),
    },
    {
        "name": 'Glass Breakwater',
        "colors": ('#1B212A', '#44BFC9', '#9BD1D8', '#262127', '#D1D2D4'),
        "positions": (0.0, 0.2622, 0.5332, 0.7859, 1.0),
    },
    {
        "name": 'Orchid Sunrise',
        "colors": ('#9C25ED', '#B248CC', '#D56FAB', '#928DF8', '#C5AFFE'),
        "positions": (0.0, 0.2783, 0.5007, 0.7288, 1.0),
    },
    {
        "name": 'Wild Menagerie',
        "colors": ('#110417', '#8A4C1F', '#DCBF93', '#E01A90', '#3DC51E', '#7EC0DD', '#F0F4E2'),
        "positions": (0.0, 0.1126, 0.2707, 0.398, 0.5926, 0.805, 1.0),
    },
    {
        "name": 'Storm Emberwake',
        "colors": ('#1F0A36', '#1C1AD9', '#34A2E8', '#CFD2D1', '#D5381B', '#F47E28', '#D7E0E3'),
        "positions": (0.0, 0.1931, 0.3594, 0.4741, 0.6706, 0.8645, 1.0),
    },
    {
        "name": 'Cinder Orchard',
        "colors": ('#1E171B', '#C64827', '#D9B03A', '#CED293', '#EE553D'),
        "positions": (0.0, 0.1712, 0.5217, 0.7403, 1.0),
    },
    {
        "name": 'Burnt Foundry',
        "colors": ('#171313', '#781A0A', '#561FA0', '#002DF9', '#5365B8', '#C6C0CE'),
        "positions": (0.0, 0.2136, 0.336, 0.555, 0.7507, 1.0),
    },
    {
        "name": 'Mosswork Hollow',
        "colors": ('#000A00', '#6C6F65', '#090A09', '#5A675B', '#B3B2A3'),
        "positions": (0.0, 0.2459, 0.5449, 0.8183, 1.0),
    },
    {
        "name": 'Satin Marquee',
        "colors": ('#1B211F', '#2F718E', '#D8C5D4', '#F03290', '#E5CB4C', '#ECDEB8'),
        "positions": (0.0, 0.158, 0.362, 0.5859, 0.8208, 0.99),
    },
    {
        "name": 'Briar Voltage',
        "colors": ('#0A0624', '#F617BB', '#9BF803'),
        "positions": (0.0625, 0.4321, 0.8406),
    },
    {
        "name": 'Cold Front',
        "colors": ('#080C0F', '#274065', '#608AC3', '#2958A1', '#DFF0FF'),
        "positions": (0.0, 0.2813, 0.4912, 0.7363, 1.0),
    },
    {
        "name": 'Undertow Plate',
        "colors": ('#050503', '#45627E', '#0071F9', '#96B0BA', '#0071F9', '#EBFAFB'),
        "positions": (0.0, 0.1712, 0.3884, 0.5764, 0.7954, 1.0),
    },
    {
        "name": 'Radioactive Melt',
        "colors": ('#E5F7FF', '#E5F7FF', '#3DFD07', '#000009'),
        "positions": (0.0, 0.3921, 0.5046, 0.8042),
    },
    {
        "name": 'Charcoal Lipstick',
        "colors": ('#838776', '#FF8CBD', '#FF0000', '#F5B6FC', '#030703'),
        "positions": (0.0, 0.2073, 0.4654, 0.8093, 1.0),
    },
    {
        "name": 'Coastal Pottery',
        "colors": ('#FFE5D6', '#80C1FF', '#497E71', '#70726F'),
        "positions": (0.0, 0.5869, 0.7998, 1.0),
    },
    {
        "name": 'Winter Trapdoor',
        "colors": ('#DDFBFF', '#C4C2FF', '#DDFBFF', '#8E96FF', '#000409'),
        "positions": (0.0, 0.0706, 0.3421, 0.4846, 0.8042),
    },
    {
        "name": 'Abyssal Lilac',
        "colors": ('#D498F6', '#0C3B59', '#051826', '#000508'),
        "positions": (0.0, 0.3042, 0.654, 1.0),
    },
    {
        "name": 'Velvet Detonation',
        "colors": ('#080500', '#080500', '#484845', '#080500', '#080500', '#EFCBF1', '#EFCBF1', '#FD3B3E', '#FC8088'),
        "positions": (0.0, 0.125, 0.2314, 0.2871, 0.4209, 0.4219, 0.7268, 0.7737, 1.0),
    },
    {
        "name": 'Welcome to the Jungle',
        "colors": ('#0C0618', '#177E4A', '#252D26', '#9CAD8F'),
        "positions": (0.0, 0.5603, 0.7671, 0.981),
    },
    {
        "name": 'Arctic Cutover',
        "colors": ('#393271', '#FFFFF6', '#00A7FF', '#050000', '#050000'),
        "positions": (0.0, 0.1568, 0.5586, 0.645, 1.0),
    },
    {
        "name": 'Silent Pewter',
        "colors": ('#010000', '#C2C0CB', '#9C9BAE', '#989DA8'),
        "positions": (0.0, 0.1562, 0.7375, 1.0),
    },
    {
        "name": 'Porcelain Beacon',
        "colors": ('#38495B', '#CBC5FD', '#FF989E', '#FFFFFF'),
        "positions": (0.0, 0.2688, 0.5806, 0.8042),
    },
    {
        "name": 'Umber Nocturne',
        "colors": ('#0A0625', '#A14529', '#AB9EAC'),
        "positions": (0.0854, 0.3079, 0.8406),
    },
    {
        "name": 'Lime Rift',
        "colors": ('#92D0FA', '#ACFA00', '#050000', '#050000'),
        "positions": (0.0, 0.332, 0.593, 1.0),
    },
    {
        "name": 'Estuary Voltage',
        "colors": ('#04F9FF', '#D528A9', '#001B2B'),
        "positions": (0.0034, 0.3592, 0.8142),
    },
)
