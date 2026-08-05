Feature: Rich pulse centering
  As a timer user
  I want the rich pulse animation to center exactly like the other pulses
  So the showcase never looks shifted by a column

  Scenario: Rich styling preserves the raw glyph widths
    Given the zero timer glyph lines
    When I style them with the rich pulse at phase 0.5
    Then every styled line has the same visible width as the raw line
    And the widest styled line equals the raw glyph width

  Scenario: Rich and ANSI pulses center identically
    Given the zero timer glyph lines
    When I style them with the rich and ansi pulses at phase 0.5
    Then both pulses need the same horizontal padding
