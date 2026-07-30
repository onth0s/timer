Feature: Duration string parsing
  As a user typing a duration on the command line
  I want the parser to convert duration strings to a total number of seconds
  So that the timer knows exactly how long to run

  Scenario Outline: Parse explicit unit strings
    Given the duration string "<input>"
    When I parse it
    Then the total seconds should be <seconds>

    Examples:
      | input   | seconds |
      | 5s      | 5       |
      | 90s     | 90      |
      | 1m      | 60      |
      | 1m30s   | 90      |
      | 1h      | 3600    |
      | 1h30m   | 5400    |
      | 1h30m0s | 5400    |
      | 2h0m0s  | 7200    |

  Scenario: Bare number is interpreted as seconds
    Given the duration string "42"
    When I parse it
    Then the total seconds should be 42

  Scenario: Short-form XhY means Xh Ym
    Given the duration string "1h30"
    When I parse it
    Then the total seconds should be 5400

  Scenario: Short-form XmY means Xm Ys
    Given the duration string "2m30"
    When I parse it
    Then the total seconds should be 150

  Scenario: Invalid duration raises an error
    Given the duration string "banana"
    When I parse it
    Then a ValueError should be raised
