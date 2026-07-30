Feature: Duration formatting
  As a timer user
  I want durations to be displayed as human-readable strings
  So I can read the summary at a glance

  Scenario Outline: Format a duration in seconds to a human string
    Given a duration of <seconds> total seconds
    When I format it
    Then the formatted string should be "<display>"

    Examples:
      | seconds | display |
      | 0       | 0s      |
      | 5       | 5s      |
      | 60      | 1m      |
      | 90      | 1m30s   |
      | 3600    | 1h      |
      | 3661    | 1h1m1s  |
      | 7200    | 2h      |
