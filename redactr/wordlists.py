"""Built-in word lists used for detection and for generating fictional surrogates.

Everything is embedded so ЯedactR works fully offline.
"""


def _set(s: str) -> set[str]:
    return {w.strip().lower() for w in s.split() if w.strip()}


# --------------------------------------------------------------------------------------
# Common first names (used to *detect* people).  Diverse on purpose.
# --------------------------------------------------------------------------------------
FIRST_NAMES = _set("""
aaron abby abdul abdullah abigail adam adrian ahmad ahmed aisha alan albert alejandro alex alexander alexandra
alexis ali alice alicia allison amanda amber amelia amir amit amy ana andre andrea andrew angela angelo anil
anita ann anna anne anthony antonio anya arjun arthur arun ashley asif aubrey audrey austin ava ayesha barbara
barry beatriz ben benjamin beth betty beverly bilal blake bob bobby brandon brenda brian brittany bruce bryan
caleb cameron carl carla carlos carmen carol caroline carolyn catherine charles charlie charlotte chelsea chen
cheryl chloe chris christian christina christine christopher cindy claire clara claudia cody colin connor
craig crystal cynthia daisy dale damian dan dana daniel danielle david dean deborah debra deepak denise dennis
derek diana diane diego dimitri dmitri dominic donald donna doris dorothy douglas dylan ed eddie edward elaine
eleanor elena eli elijah elizabeth ella ellen emily emma eric erica erin ethan eugene eva evan evelyn faisal
farah fatima felix fernando fiona francesca francis frank gabriel gabriela gail gary gavin george gerald
gina giovanni gloria gordon greg gregory hamza hannah harold harry hassan heather helen henry hiroshi holly
howard hugo hussain ian imran irene isaac isabel isabella ivan jack jackson jacob jacqueline jake james jamie
jane janet janice jared jasmine jason javier jay jean jeff jeffrey jennifer jenny jeremy jerry jesse jessica
jesus jill jim jimmy joan joanna joe joel john johnny jon jonathan jordan jorge jose joseph joshua joyce juan
judith judy julia julian julie justin kamal karen karim kate katherine kathleen kathryn kathy katie kayla
keith kelly ken kenji kenneth kevin khalid kim kimberly kyle laura lauren lawrence leah lee leo leon leonardo
liam lily linda lisa logan lori louis lucas lucy luis luke lynn madison maggie mahmoud manuel marco marcus
margaret maria marie marilyn mario marisa martha martin mary mason matthew maya megan melissa michael michelle
miguel mike mohamed mohammad mohammed mona monica muhammad nadia nancy naomi natalie nathan neha nicholas
nicole nikhil nina noah nora olga oliver olivia omar oscar owen pablo pamela patricia patrick paul paula
pedro peter philip phillip pooja priya rachel rafael rahul raj rajesh ralph ramesh randy raymond rebecca
reza ricardo richard rick ritu robert roberto robin rodrigo roger ronald rosa ross roy ruby russell ruth
ryan sadia saeed sam samantha samir samuel sandra sanjay sara sarah scott sean sergei sergio shannon sharon
shawn sheila shirley simon sofia sonia sophia sophie stacy stanley stephanie stephen steve steven stuart
sunil susan suzanne sylvia tamara tanya tara taylor teresa terry thomas tiffany tim timothy tina todd tom
tony tracy travis tyler usman valerie vanessa veronica victor victoria vijay vikram vincent virginia vivek
walter wayne wei wendy william xavier yasmin yusuf yvonne zachary zainab zara zoe ahad bilqis tariq naveed
saima rashid shahid waqar zubair nasir kashif adeel junaid
""")

# Names that are also everyday English words - only treated as a name when followed by a surname
AMBIGUOUS_FIRST = _set("""
will may mark grace bill frank rich hope june april joy faith dawn summer rose lily ruby amber crystal
sandy dean art bob jack lee chase grant miles rob sue pat ray gene glen rod victor jay eve max
destiny guy hunter jean robin skip skye stone sunny taylor holly penny page lane august
""")

HONORIFICS = ["Mr", "Mrs", "Ms", "Miss", "Mx", "Dr", "Prof", "Professor", "Sir", "Dame", "Madam", "Mme",
              "Mister", "Lord", "Lady", "Rev", "Hon", "Sr", "Jr"]

# --------------------------------------------------------------------------------------
# Common English words - used to avoid flagging ordinary capitalised words as names
# --------------------------------------------------------------------------------------
COMMON_WORDS = _set("""
a about above according account accounts across action actions active activity actual add added additional
address admin administration after afternoon again against agenda agreement all also although always am
amount an analysis and annual another answer any appendix application approach approval approved april are
area areas as ask assessment asset assets at attached attachment audit august authority available average
back background balance bank base based basis be because been before being below benefit benefits best
better between board body both brief budget business but by calendar call can capital card case cash
category center central chair change changes chapter chart check chief city client close closing code
committee common company comparison compliance conclusion confidential consider contact content contents
contract control corporate cost costs could council country cover credit current customer daily data date
day days dear december decision department description design detail details development did director
discussion division do document does done draft due during each early east either email employee end
engineering enterprise entire equipment estimate evaluation even event every example executive expected
expense expenses external facility fact factor february fee field figure file final finance financial
first fiscal following for form forward friday from full fund funding future general global goal goals
good government grand gross group growth guide had has have he head health help her here high his history
home hour hours how however human i if impact implementation important in include including income index
industry information initial input inside instructions insurance internal into introduction investment
invoice is issue issues it item items its january job joint july june just key labor last law lead
leadership legal less letter level liability limited line list loan local long low main maintenance
management manager march market marketing material may me meeting member memo method methods middle might
minutes model monday month monthly more morning most must my name national net new news next no none
north not note notes notice november now number objective objectives october of off office officer
officers on one only open operating operations option or order organization other our out outcome output
over overall overview owner page paid part partner parties party payment people per percent period person
personal phase plan planning please point policy portfolio position post president price principal
priority private process product production products profit program project projects proposal provide
public purchase purpose q1 q2 q3 q4 quality quarter quarterly question questions rate re reason recommendation
recommendations record reference regards region regional related release remarks report reports request
required requirements research resource resources response result results return revenue review risk
risks role sale sales saturday schedule scope second section security see senior september service services
session she should signature since site so software some source south staff standard start statement
status step steps strategy subject subtotal success such summary sunday supplier supply support system
systems table target task tasks tax team technical technology term terms test than thank thanks that the
their them then there these they this those thursday time title to today total training transfer
treasurer tuesday two type under unit until update updated us use user value vendor version vice view
was we wednesday week weekly well were west what when where which while who why will with within without
work working would year yearly years yes yet you your yours sincerely best kind warm cheers hello hi dear
team all everyone attendees present absent action items next steps background purpose scope objectives
inc llc ltd corp corporation company co group holdings plc llp gmbh ag sa bv pty pvt
monday tuesday wednesday thursday friday saturday sunday january february march april june july august
september october november december jan feb mar apr jun jul aug sep sept oct nov dec mon tue wed thu fri sat sun
ai api ceo cfo coo cto cio cmo hr it pr qa kpi roi sla faq pdf csv url ok usa uk eu
phone email e-mail mobile fax website salary department city company address employee contact
yes no n/a tbd tba etc ie eg vs pm am id no. ref mr mrs ms mx dr prof sir dame madam miss rev hon sr jr st
""")

US_STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
             "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
             "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
             "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
             "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
             "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
             "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia"]

US_STATE_CODES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM "
                  "NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC").split()

COUNTRIES = ["Afghanistan", "Argentina", "Australia", "Austria", "Bangladesh", "Belgium", "Brazil", "Canada",
             "Chile", "China", "Colombia", "Denmark", "Egypt", "Finland", "France", "Germany", "Greece",
             "Hong Kong", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy", "Japan", "Jordan",
             "Kenya", "Kuwait", "Malaysia", "Mexico", "Morocco", "Netherlands", "New Zealand", "Nigeria",
             "Norway", "Oman", "Pakistan", "Peru", "Philippines", "Poland", "Portugal", "Qatar", "Romania",
             "Russia", "Saudi Arabia", "Singapore", "South Africa", "South Korea", "Spain", "Sri Lanka",
             "Sweden", "Switzerland", "Taiwan", "Thailand", "Turkey", "Ukraine", "United Arab Emirates", "UAE",
             "United Kingdom", "United States", "Vietnam", "England", "Scotland", "Wales"]

CITIES = ["New York City", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio",
          "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "San Francisco", "Columbus", "Seattle",
          "Denver", "Boston", "Detroit", "Nashville", "Portland", "Las Vegas", "Baltimore", "Milwaukee",
          "Atlanta", "Miami", "Minneapolis", "Cleveland", "Pittsburgh", "Cincinnati", "Orlando", "Tampa",
          "Charlotte", "Raleigh", "Sacramento", "Salt Lake City", "Arlington", "Alexandria", "Richmond",
          "Washington D.C.", "Washington DC", "London", "Manchester", "Birmingham", "Edinburgh", "Glasgow",
          "Dublin", "Paris", "Berlin", "Munich", "Frankfurt", "Hamburg", "Madrid", "Barcelona", "Rome", "Milan",
          "Amsterdam", "Brussels", "Zurich", "Geneva", "Vienna", "Stockholm", "Oslo", "Copenhagen", "Helsinki",
          "Warsaw", "Prague", "Lisbon", "Athens", "Istanbul", "Moscow", "Dubai", "Abu Dhabi", "Doha", "Riyadh",
          "Jeddah", "Cairo", "Lagos", "Nairobi", "Johannesburg", "Cape Town", "Karachi", "Lahore", "Islamabad",
          "Mumbai", "Delhi", "New Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune",
          "Dhaka", "Singapore", "Kuala Lumpur", "Jakarta", "Bangkok", "Manila", "Hong Kong", "Shanghai",
          "Beijing", "Shenzhen", "Tokyo", "Osaka", "Seoul", "Sydney", "Melbourne", "Brisbane", "Perth",
          "Auckland", "Toronto", "Vancouver", "Montreal", "Calgary", "Ottawa", "Mexico City", "Sao Paulo",
          "Rio de Janeiro", "Buenos Aires", "Santiago", "Lima", "Bogota"]

ORG_SUFFIXES = ["Inc", "Incorporated", "LLC", "L.L.C.", "Ltd", "Limited", "Corp", "Corporation", "Company", "Co",
                "Group", "Holdings", "Technologies", "Technology", "Systems", "Solutions", "Partners",
                "Associates", "Bank", "Capital", "Ventures", "Labs", "Consulting", "Industries", "International",
                "Enterprises", "Foundation", "University", "College", "Institute", "Hospital", "Clinic", "Agency",
                "Authority", "Trust", "Fund", "Insurance", "Pharmaceuticals", "Pharma", "Motors", "Airlines",
                "Logistics", "Networks", "Media", "Studios", "Services", "GmbH", "AG", "PLC", "LLP", "LP", "S.A.",
                "SA", "BV", "N.V.", "Pty", "Pvt"]

# --------------------------------------------------------------------------------------
# Pools for generating fictional surrogates (deliberately bland / invented)
# --------------------------------------------------------------------------------------
SURROGATE_FIRST = """Avery Blake Callum Darcy Elliot Finley Greer Harlow Indigo Jensen Kendall Linden Marlow
Nolan Oakley Perrin Quinlan Rowan Sutton Tamsin Upton Vesper Wilder Xander Yardley Zephyr Ainsley Briar
Corin Delphine Emrys Fenwick Galen Halston Iolanthe Jasper Kestrel Lorcan Maren Niamh Orrin Pellam Quincy
Rhiannon Soren Thaddeus Ursa Vaughn Wren Ximena Yorick Zinnia Anselm Bexley Cosima Dashiell Eldon Fable
Gideon Hollis Ione Juno Kit Leander Merritt Nerys Ottoline Piers Rafferty Sabine Tobias Ulric Valen Waverly
Ysolde Zev Alder Brielle Caspian Delia Evander Faye Garrick Hesper Isolde Jory Keziah Lysander Mireille
Nico Odessa Percival Roswell Seraphina Tiernan Verity Wystan""".split()

SURROGATE_LAST = """Ashdown Bellweather Carrow Dunmore Everhart Fairbrook Glenhaven Hartwell Ironside Juniper
Kettering Larkspur Merriweather Northcott Oakhurst Pemberton Quillfeather Ravensworth Silverton Thornbury
Underwood Vantreight Whitlock Yarrowby Zellner Ambrose Blackwood Coldwell Driscoll Ellsworth Fennimore
Galloway Hollingsworth Inglewood Jessop Kingsley Lockridge Marchetti Nethercott Osterfield Prescott
Quarrington Redgrave Stanmore Tolliver Upshaw Valcourt Westbrook Yelverton Zimmerly Alderidge Brightwater
Castellan Dovecote Easterly Foxworth Greystone Hawthorne Islington Jarrow Kenwright Lindqvist Moorcroft
Norwood Orchardson Pickering Ravenhill Sedgewick Thistlewood Umberfield Vickery Wolcott Yeoman Ashcombe
Birchall Copperfield Delacroix Elmsworth Farnham Goldwyn Holloway Ivesdale Kimbrough Lowell Montague
Northam Ormsby Penhallow Rookwood Stoneleigh Trevelyan Wexford""".split()

SURROGATE_ORG_CORE = """Northwind Bluepeak Silverline Ironbridge Cobaltia Larkfield Quillstone Brightmoor
Halcyon Vantage Meridian Nimbus Orchardia Pinecrest Redwater Stellaris Tidewell Umbra Verdant Westerly
Zenithal Amberlake Boreal Cascadia Driftwood Emberly Foxglove Granitex Harborview Indigo Junction Keystone
Lumina Monarch Northstar Oakline Paragon Quantix Riverstone Summitry Talon Uplands Vireo Willowmere Axiom
Beacon Crestwood Dovetail Equinox Fernhill Glacier Highmark Ivory Jadeite Kingfisher Lodestar Mosaic
Nautilus Obsidian Pinnacle Radiant Sapphire Trellis Unison Vertex Wavecrest Yellowfin Zephyrus""".split()

SURROGATE_ORG_SUFFIX = ["Holdings", "Group", "Partners", "Labs", "Industries", "Ventures", "Systems",
                        "Analytics", "Dynamics", "Corp"]

SURROGATE_CITIES = """Ashbury Brookhaven Calder Falls Dunmere Elmstead Fairmoor Glenrock Harrowgate Ivydale
Juniper Bay Kingsmere Larchmont Hollow Millbrook Northfield Oakvale Pinehurst Quarry Hill Riverbend Stonebridge
Thornfield Umberton Valemont Westmarch Yewdale Ambervale Bramblewood Coppergate Dovercourt Eastmere
Foxhollow Greywater Highcliff Ironvale Kestrel Point Lindenfield Meadowcross""".split("\n")

SURROGATE_STREETS = ["Maple", "Juniper", "Willow", "Harbor", "Lantern", "Orchard", "Copper", "Meadow",
                     "Briar", "Falcon", "Heron", "Summit", "Linden", "Ember", "Cedar", "Quarry", "Hollow",
                     "Thistle", "Ridgeview", "Bramble", "Larch", "Pebble", "Saffron", "Tamarack"]

STREET_SUFFIXES = ["Street", "Avenue", "Road", "Lane", "Drive", "Court", "Way", "Place", "Boulevard",
                   "Terrace", "Parkway", "Circle"]


def _flatten_cities():
    out = []
    for line in SURROGATE_CITIES:
        # lines contain single-word and two-word names; split on double meaning carefully
        words = line.split()
        i = 0
        while i < len(words):
            w = words[i]
            if i + 1 < len(words) and words[i + 1] in ("Falls", "Bay", "Hollow", "Hill", "Point"):
                out.append(w + " " + words[i + 1])
                i += 2
            else:
                out.append(w)
                i += 1
    return out


SURROGATE_CITY_LIST = _flatten_cities()
