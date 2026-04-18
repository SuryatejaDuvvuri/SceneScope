import re
from typing import Optional
from screenplay_tools.fountain.parser import Parser
from screenplay_tools.fountain.writer import Writer

class ParsedScene:
    def __init__(self, sceneNumber: int, heading: Optional[str], description: str,
                 interiorExterior: Optional[str] = None, location: Optional[str] = None, timeDay: Optional[str] = None):
        self.sceneNumber = sceneNumber
        self.heading = heading
        self.description = description
        self.interiorExterior = interiorExterior
        self.location = location
        self.timeDay = timeDay
    def __repr__(self):
        return (f"ParsedScene(sceneNumber={self.sceneNumber},\n  heading={self.heading!r},\n  description={self.description!r},\n"
                f"  interiorExterior={self.interiorExterior!r}, location={self.location!r}, timeDay={self.timeDay!r})")


script = f"""
INT. CAMPUS BAR - NIGHT

MARK ZUCKERBERG is a sweet looking 19 year old whose lack of
any physically intimidating attributes masks a very
complicated and dangerous anger. He has trouble making eye
contact- and sometimes it's hard to tell if he's talking to you
or to himself.

ERICA, also 19, is Mark's date. She has a girl-next-door face
that makes her easy to fall for. At this point in the
conversation she already knows that she'd rather not be there
and her politeness is about to be tested.

The scene is stark and simple.
"""
parser = Parser()
writer = Writer()


parser.add_text(script)

formatted_script = writer.write(parser.script)

def parseHeading(heading: str):
    match = re.match(r'^(INT\.|EXT\.|INT/EXT\.)\s*(.*?)\s*-\s*(.*)$', heading)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None, None, None

def buildScene(sceneNumber, heading, descriptionLines):
    interiorExterior, location, timeDay = parseHeading(heading) if heading else (None, None, None)
    return ParsedScene(
        sceneNumber=sceneNumber,
        heading=heading,
        description="\n".join(descriptionLines),
        interiorExterior=interiorExterior,
        location=location,
        timeDay=timeDay
    )

scenes = []
sceneNumber = 1
currentHeading = None
descriptionLines = []
collectingDescription = False
hasHeading = False

for element in parser.script.elements:
    sceneType = element.__class__.__name__
    if sceneType == "SceneHeading":
        hasHeading = True
        if currentHeading is not None:
            scenes.append(buildScene(sceneNumber, currentHeading, descriptionLines))
            sceneNumber += 1
        currentHeading = element.text
        descriptionLines = []
        collectingDescription = True
    elif sceneType == "Action":
        if collectingDescription or not hasHeading:
            descriptionLines.append(element.text)
    elif sceneType in ("Dialogue", "Character", "Parenthetical", "Transition"):
        collectingDescription = False

if currentHeading is not None:
    scenes.append(buildScene(sceneNumber, currentHeading, descriptionLines))
elif not hasHeading and descriptionLines:
    scenes.append(buildScene(1, None, descriptionLines))

for scene in scenes:
    print(scene)

