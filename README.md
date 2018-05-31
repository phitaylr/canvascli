# Canvas CLI

This is a CLI utility for interacting with the Canvas API.

## Commands:

| Command             | Description                                          |
|---------------------|------------------------------------------------------|
| archive             | Move courses to archived term                        |
| deletecoursesbyterm | Delete all courses in a term                         |
| deleteunused        | Delete unused courses from Unused Courses csv report |
| renwebexport        | Prepare RenWeb export file                           |
| reportnoduedates    | Report published assignments with no due dates       |

## Configuration

The only configuration needed is api credentials. Make a file called .canvasclicred.json in the user home directory. Then add your instance and api key.
```
{
  "url": "https://INSTANCE.instructure.com/api/v1/",
  "auth": "YOUR API KEY"
}
```

## Installation
Do ```pip install .``` to install scripts and ependencies.
