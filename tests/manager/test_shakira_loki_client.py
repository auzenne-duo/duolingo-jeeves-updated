import io
import json
import os

from jeeves.manager.shakira_loki import ShakiraLokiApiClient


def test_parse_jira_issue():
    """
    Tests that the parser correctly extracts the relevant information from the Jira issue description
    """
    file_path = os.path.join(os.path.dirname(__file__), "jira_api_response_ios.json")

    with open(file_path) as f:
        client = ShakiraLokiApiClient()
        jira_issue = json.load(f)
        summary = jira_issue["fields"]["description"]["content"]
        expected_response = [
            ["app version", "7.49.0.0"],
            ["iOS version", "18.0"],
            ["device model", "iPhone"],
            ["platform", "Simulator"],
            ["raw platform", "arm64"],
            ["ui language", "en-us"],
            ["screen", "375 W x 667 H"],
            ["environment", "Simulator (com.duolingo.DuolingoMobile.berrybus01)"],
            ["jail broken", "false"],
            ["id", "504909438"],
            [
                "diagnostic page",
                "",
                "https://diagnostics.duolingo.com/user-summary/504909438?show_activity=true",
            ],
            ["email", "nancy@duolingo.com"],
            ["username", "berrybus01"],
            ["current course", "MUSIC_MT (none <- English)"],
            ["time zone", "America/New_York"],
            ["service mappings", "none"],
            ["Tutors server", "Production"],
            ["Subscription status", "Super"],
            ["Mega course", "music"],
            ["debug tools fab created", "true"],
            ["session url", "No session recorded"],
        ]
        actual_response = client.extract_iOS_reporter_information(summary)
        assert actual_response == expected_response


def test_parse_ios_log():
    log = """
    2024/11/11 16:06:54:729  [RET] Writing 577653710 currentStreak=Optional(Bedrock.Streak(length: 96, startDate: <TimelineRelativeDate 2024-7-29>, endDate: <TimelineRelativeDate 2024-11-11>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-11-11>))) previousStreak=Optional(Bedrock.Streak(length: 1, startDate: <TimelineRelativeDate 2024-7-6>, endDate: <TimelineRelativeDate 2024-7-8>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-7-6>))) longestStreak=Optional(Bedrock.LifetimeStreak(length: 115, startDate: Optional(<TimelineRelativeDate 2021-9-16>), endDate: Optional(<TimelineRelativeDate 2022-1-16>), achieveDate: nil))
    2024/11/11 16:06:54:729  [RET] [UHM] messaging-backend returned the following messages HomeMessageRanking(messages: [DuolingoMobile.HomeMessageRanking.Message(messageId: "pathMigration", additionalDataJSON: Optional(["fromLanguageId": , "learningLanguageId": ]), numTimesSeenBefore: Optional(0)), DuolingoMobile.HomeMessageRanking.Message(messageId: "pathChange", additionalDataJSON: Optional(["fromLanguageId": , "learningLanguageId": ]), numTimesSeenBefore: Optional(0)), DuolingoMobile.HomeMessageRanking.Message(messageId: "plusFamilyMemberWelcome", additionalDataJSON: Optional([:]), numTimesSeenBefore: Optional(0)), DuolingoMobile.HomeMessageRanking.Message(messageId: "resurrectionDogfoodingNag", additionalDataJSON: Optional([:]), numTimesSeenBefore: Optional(1))])
    2024/11/11 16:06:54:735  [RENG] Widget streak data updated to 96.
    2024/11/11 16:06:54:735  [RENG] Widget state updated to extended.
    2024/11/11 16:06:54:737  [RET] Storing streaks on the disk for user 577653710, streaks are StoredStreaks(currentStreak: Optional(Bedrock.Streak(length: 96, startDate: <TimelineRelativeDate 2024-7-29>, endDate: <TimelineRelativeDate 2024-11-11>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-11-11>))), previousStreak: Optional(Bedrock.Streak(length: 1, startDate: <TimelineRelativeDate 2024-7-6>, endDate: <TimelineRelativeDate 2024-7-8>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-7-6>))), longestStreak: Optional(Bedrock.LifetimeStreak(length: 115, startDate: Optional(<TimelineRelativeDate 2021-9-16>), endDate: Optional(<TimelineRelativeDate 2022-1-16>), achieveDate: nil)))
    """

    expected_values = [
        [
            "1731341214729000192",
            "[RET] Writing 577653710 currentStreak=Optional(Bedrock.Streak(length: 96, startDate: <TimelineRelativeDate 2024-7-29>, endDate: <TimelineRelativeDate 2024-11-11>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-11-11>))) previousStreak=Optional(Bedrock.Streak(length: 1, startDate: <TimelineRelativeDate 2024-7-6>, endDate: <TimelineRelativeDate 2024-7-8>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-7-6>))) longestStreak=Optional(Bedrock.LifetimeStreak(length: 115, startDate: Optional(<TimelineRelativeDate 2021-9-16>), endDate: Optional(<TimelineRelativeDate 2022-1-16>), achieveDate: nil))",
        ],
        [
            "1731341214729000192",
            '[RET] [UHM] messaging-backend returned the following messages HomeMessageRanking(messages: [DuolingoMobile.HomeMessageRanking.Message(messageId: "pathMigration", additionalDataJSON: Optional(["fromLanguageId": , "learningLanguageId": ]), numTimesSeenBefore: Optional(0)), DuolingoMobile.HomeMessageRanking.Message(messageId: "pathChange", additionalDataJSON: Optional(["fromLanguageId": , "learningLanguageId": ]), numTimesSeenBefore: Optional(0)), DuolingoMobile.HomeMessageRanking.Message(messageId: "plusFamilyMemberWelcome", additionalDataJSON: Optional([:]), numTimesSeenBefore: Optional(0)), DuolingoMobile.HomeMessageRanking.Message(messageId: "resurrectionDogfoodingNag", additionalDataJSON: Optional([:]), numTimesSeenBefore: Optional(1))])',
        ],
        ["1731341214734999808", "[RENG] Widget streak data updated to 96."],
        ["1731341214734999808", "[RENG] Widget state updated to extended."],
        [
            "1731341214736999936",
            "[RET] Storing streaks on the disk for user 577653710, streaks are StoredStreaks(currentStreak: Optional(Bedrock.Streak(length: 96, startDate: <TimelineRelativeDate 2024-7-29>, endDate: <TimelineRelativeDate 2024-11-11>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-11-11>))), previousStreak: Optional(Bedrock.Streak(length: 1, startDate: <TimelineRelativeDate 2024-7-6>, endDate: <TimelineRelativeDate 2024-7-8>, lastExtendedDate: Optional(<TimelineRelativeDate 2024-7-6>))), longestStreak: Optional(Bedrock.LifetimeStreak(length: 115, startDate: Optional(<TimelineRelativeDate 2021-9-16>), endDate: Optional(<TimelineRelativeDate 2022-1-16>), achieveDate: nil)))",
        ],
    ]
    client = ShakiraLokiApiClient()

    file_stream = io.BytesIO(str.encode(log))
    text_stream = io.TextIOWrapper(file_stream, encoding="utf-8")

    parsed_values = client.parse_logs_ios(text_stream)

    assert expected_values == parsed_values


def test_parse_jira_issue_android():
    """
    Tests that the parser correctly extracts the relevant information from the Jira issue description
    """
    file_path = os.path.join(os.path.dirname(__file__), "jira_api_response_android.json")

    with open(file_path) as f:
        client = ShakiraLokiApiClient()
        jira_issue = json.load(f)
        summary = jira_issue["fields"]["description"]["content"]
        expected_response = [
            ["Platform", " Android"],
            ["App version code", " 6.10.0d (2009) play"],
            ["API Level", " 34"],
            ["OS Version", " 6.1.23-android14-4-00257-g7e35917775b8-ab9964412 (12077443)"],
            ["Host (Device)", " r-d3d21742fc70d910-p10v (emu64a)"],
            ["Model (Product)", " sdk_gphone64_arm64 (sdk_gphone64_arm64)"],
            ["Screen", " 1440x2891, 560dpi"],
            ["Config", " Internal, 192 | 576"],
            ["Device language", " zh_CN"],
            ["Default device language", " en_US"],
            ["Performance mode", " MIDDLE"],
            ["CourseId", " DUOLINGO_FR_ZH-CN"],
            ["Username", " GuanhuaLi1"],
            ["Tags", " BET40189 PS6T3BRN"],
            ["CourseSubject", " language"],
            ["Course", " French <- Chinese"],
            ["User ID", " 909564076"],
            ["Diagnostics page", " "],
            ["url", "https://diagnostics.duolingo.com/user-summary/909564076?show_activity=true"],
            ["Build Type", " BETRC40190"],
            [
                "FullStory Session if recording",
                " FullStory link is unavailable because we're not sure why actually",
            ],
            ["Activity", " com.duolingo.splash.LaunchActivity"],
        ]
        actual_response = client.extract_android_reporter_information(summary)
        assert actual_response == expected_response


def test_parse_android_log():
    log = """2024-12-05 18:16:45.728-0500 [INFO | Platform - Application Stability and Performance]: Tracking timer event lesson_start with duration of 2433 ms
2024-12-05 18:16:45.725-0500 [INFO | Platform - Application Stability and Performance]: endAsyncSection: splash_to_ready
2024-12-05 18:16:45.725-0500 [INFO | Platform - Application Stability and Performance]: endAsyncSection: lesson_start
2024-12-05 18:16:45.724-0500 [INFO | Platform - Application Stability and Performance]: endAsyncSection: prefetch_lesson_start
2024-12-05 18:16:45.529-0500 [INFO | Platform - Application Stability and Performance]: endSection: api_call https://android-api.duolingo.com/users/192897876/daily-quests?timezone=America%2FNew_York
2024-12-05 18:16:45.505-0500 [INFO | Platform - Application Stability and Performance]: endAsyncSection: challenge_continue
2024-12-05 18:16:45.505-0500 [VERBOSE | Platform - Application Stability and Performance]: Resumed: MathPatternTableFragment
2024-12-05 18:16:45.504-0500 [VERBOSE | Platform - Application Stability and Performance]: Resumed: GradingRibbonFragment
2024-12-05 18:16:45.504-0500 [VERBOSE | Platform - Application Stability and Performance]: Resumed: ChallengeButtonsFragment"""

    expected_values = [
        [
            "1733440605728000000",
            "[INFO | Platform - Application Stability and Performance]: Tracking timer event lesson_start with duration of 2433 ms",
        ],
        [
            "1733440605724999936",
            "[INFO | Platform - Application Stability and Performance]: endAsyncSection: splash_to_ready",
        ],
        [
            "1733440605724999936",
            "[INFO | Platform - Application Stability and Performance]: endAsyncSection: lesson_start",
        ],
        [
            "1733440605724000000",
            "[INFO | Platform - Application Stability and Performance]: endAsyncSection: prefetch_lesson_start",
        ],
        [
            "1733440605528999936",
            "[INFO | Platform - Application Stability and Performance]: endSection: api_call https://android-api.duolingo.com/users/192897876/daily-quests?timezone=America%2FNew_York",
        ],
        [
            "1733440605505000192",
            "[INFO | Platform - Application Stability and Performance]: endAsyncSection: challenge_continue",
        ],
        [
            "1733440605505000192",
            "[VERBOSE | Platform - Application Stability and Performance]: Resumed: MathPatternTableFragment",
        ],
        [
            "1733440605504000000",
            "[VERBOSE | Platform - Application Stability and Performance]: Resumed: GradingRibbonFragment",
        ],
        [
            "1733440605504000000",
            "[VERBOSE | Platform - Application Stability and Performance]: Resumed: ChallengeButtonsFragment",
        ],
    ]
    client = ShakiraLokiApiClient()

    file_stream = io.BytesIO(str.encode(log))
    text_stream = io.TextIOWrapper(file_stream, encoding="utf-8")

    parsed_values = client.parse_logs_android(text_stream)

    assert expected_values == parsed_values
