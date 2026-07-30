Feature: Glyph width consistency
  As a timer user
  I want every rendered glyph line to have the same width
  So the display never shifts or jitters as digits change

  Scenario Outline: All glyph lines within a time string have equal width
    Given the time value <seconds>
    When I render it as a count-up display
    Then every line in the glyph output should have the same width

    Examples:
      | seconds |
      | 0       |
      | 1       |
      | 9       |
      | 10      |
      | 59      |
      | 60      |
      | 99      |
      | 3599    |
      | 3600    |
      | 9999    |

  Scenario Outline: All glyph lines within a countdown MM:SS value have equal width
    Given the time value <seconds>
    When I render it as a countdown display
    Then every line in the glyph output should have the same width

    Examples:
      | seconds |
      | 0       |
      | 1       |
      | 59      |
      | 60      |
      | 3599    |

  Scenario: Display width does not change between consecutive seconds (no jitter)
    Given the time values 9 and 10 rendered as count-up
    Then both renderings should have the same total width

  Scenario Outline: No jitter between consecutive seconds (count-up)
    Given the consecutive time values <a> and <b> rendered as count-up
    Then both renderings should have the same total width

    Examples:
      | a | b |
      | 0 | 1 |
      | 1 | 2 |
      | 2 | 3 |
      | 3 | 4 |
      | 4 | 5 |
      | 5 | 6 |
      | 6 | 7 |
      | 7 | 8 |
      | 8 | 9 |
      | 9 | 10 |

  Scenario Outline: No jitter between consecutive seconds (countdown)
    Given the consecutive time values <a> and <b> rendered as countdown
    Then both renderings should have the same total width

    Examples:
      | a  | b  |
      | 0  | 1  |
      | 1  | 2  |
      | 9  | 10 |
      | 59 | 60 |
