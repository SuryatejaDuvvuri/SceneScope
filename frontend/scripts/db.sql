CREATE TABLE projects
(
    id UUID PRIMARY KEY,
    title VARCHAR(255),
    genre VARCHAR(50),
    time_period VARCHAR(255),
    films TEXT,
    tone TEXT,
    created_at VARCHAR(255),
    updated_at VARCHAR(255)
);

CREATE TABLE characters
(
    id UUID PRIMARY KEY,
    projectId UUID REFERENCES projects(id),
    name TEXT,
    role TEXT,
    age TEXT,
    description TEXT,
    image_url URL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE scenes
(
    id TEXT PRIMARY KEY,
    projectId UUID REFERENCES projects(id),
    scene INTEGER,
    heading TEXT,
    description TEXT,
    mood TEXT,
    image_desc TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
