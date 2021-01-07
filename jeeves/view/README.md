# Shakira routes documentation

`GET api/1/shakira/features`

Get a list of possible values for the "feature" field for the project.

### Parameters

```
project: DLAA, DLAI
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

Either create an issue in JIRA or post the screenshot to slack, depending on the feature and slack_channel fields. If neither field is set, the default behavior is to post to JIRA. Content-type is `multipart/form-data`

### Form parameters

**name**: issueData **content-type**: application/json

example:

```
{
    "reporterEmail" optional: Admin email of the user submitting the issue.
    "summary" required: Rougly one-sentence summary of the issue.
    "description" required: Longer user-provided description.
    "generatedDescription" optional: Generated information such as app version, fullstory url, session type, etc. It's a valid option to not
    set this and include this information in the "description" field.
    "feature" optional: Feature affected by the issue; e.g. Achievements, Stories, Leaderboards. Must be a value sent by the shakira/features endpoint.
    "slack_channel" optional: e.g. #visual-polish. If this is set, override the feature and post in this channel.
    "project" required: "DLAA", "DLAI".
    "preRelease" optional: Boolean; Should be "True" if reporting from TestFlight or Android pre-release build. Default value is "False".
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
    "slackChannel": Channel the screenshot and info was posted in; e.g. #visual-polish
}
```
