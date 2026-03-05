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

parsedScenes = []
sceneNumber = 1
currentHeading = None
descriptionLines = []
bodyLines = []
currentDescription = False
hasHeading = False

for element in parser.script.elements:
    sceneType = element.__class__.__name__
    if sceneType == "SceneHeading":
        hasHeading = True
        if currentHeading is not None:
            parsedScenes.append(
                ParsedScene(
                    sceneNumber=sceneNumber,
                    heading=currentHeading,
                    description="\n".join(descriptionLines)
                )
            )
            sceneNumber += 1

        currentHeading = element.text
        descriptionLines = []
        bodyLines = []
        currentDescription = True
    elif sceneType == "Action":
        if currentDescription or not hasHeading:
            descriptionLines.append(element.text)
        bodyLines.append(element.text)
    elif sceneType in ("Dialogue", "Character", "Parenthetical", "Transition"):
        currentDescription = False
        bodyLines.append(getattr(element, 'text', ''))


if hasHeading and currentHeading is not None:
    parsedScenes.append(
        ParsedScene(
            sceneNumber=sceneNumber,
            heading=currentHeading,
            description="\n".join(descriptionLines)
        )
    )
elif not hasHeading and descriptionLines:
    parsedScenes.append(
        ParsedScene(
            sceneNumber=1,
            heading=None,
            description="\n".join(descriptionLines)
        )
    )

def parseHeading(heading: str):
    match = re.match(r'^(INT\.|EXT\.|INT/EXT\.)\s*(.*?)\s*-\s*(.*)$', heading)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None, None, None
finalScenes = []
for scene in parsedScenes:
    interiorExterior, location, timeDay = parseHeading(scene.heading)
    finalScenes.append(
        ParsedScene(
            sceneNumber=scene.sceneNumber,
            heading=scene.heading,
            description=scene.description,
            interiorExterior=interiorExterior,
            location=location,
            timeDay=timeDay
        )
    )

for scene in finalScenes:
    print(scene)

