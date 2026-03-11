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
