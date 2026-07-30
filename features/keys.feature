Feature: Keyboard input interpretation
  As a timer user
  I want my keystrokes to control the timer correctly
  So that I can pause, resume, quit, and adjust time without side effects

  Scenario Outline: Pause keys are recognised
    Given the key "<key>"
    When I check if it is a pause key
    Then the result should be <result>

    Examples:
      | key    | result |
      | " "    | true   |
      | p      | true   |
      | k      | true   |
      | enter  | true   |
      | newline| true   |
      | q      | false  |
      | +      | false  |
      | -      | false  |

  Scenario Outline: Time-adjust keys are recognised
    Given the key "<key>"
    When I check if it is a time-adjust key
    Then the result should be <result>

    Examples:
      | key | result |
      | +   | true   |
      | =   | true   |
      | -   | true   |
      | " " | false  |
      | q   | false  |

  Scenario Outline: Time adjustment values
    Given the key "<key>"
    When I get the time adjustment
    Then the adjustment should be <delta> seconds

    Examples:
      | key | delta |
      | +   | 30    |
      | =   | 30    |
      | -   | -30   |
