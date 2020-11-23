## Shakira routes documentation

---

`GET api/1/shakira/features`

Get a list of possible values for the "feature" field for the project.

#### Prameters

```
project: DLAA, DLAI or DLAW
```

### Response

example:

```
{
    "features": ["Acheivements", "Audio Lessons", ...]
}
```

---

`POST api/1/shakira/report_issue`

Creates an issue in JIRA. Content-type is `multipart/form-data`

### Form parameters

**name**: issueData **content-type**: application/json

example:

```
{
    "reporterEmail": Admin email of Duo submitting the issue.
    "summary": ~One sentence summary of the issue.
    "description": Longer user-provided description.
    "generatedDescription": Generated information such as app version, fullstory url, session type, etc.
    "feature": Feature affected by the issue; e.g. Achievements, Stories, Leaderboards. Must be a value sent by the shakira/features endpoint.
    "project": "DLAA", "DLAI" or "DLAW".
    "preRelease": Boolean; Should be "True" if reporting from TestFlight or Android pre-release build. Default value is "False".
}
```

---

**name**: screenshot

Image captured of the screen when the phone was shaken

_Include any other files you want to attach in this form as well_

### Response

```
{
    "issueKey": key of the created issue; e.g. "DLAI-5467"
}
```
