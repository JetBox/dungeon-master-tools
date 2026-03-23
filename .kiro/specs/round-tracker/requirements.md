# Requirements Document

## Introduction

The Round Tracker is a new tab in the TTRPG DM Tool application for tracking time-limited events during dungeon crawls. It allows the Dungeon Master to add named items with a round countdown (e.g. torch duration, spell duration, random encounter timers) and view them in a scrollable list of widgets. This initial scope covers adding new items via a modal form and displaying them in the view.

## Glossary

- **Round_Tracker**: The tab view within the application dedicated to tracking round-based events.
- **Round_Tracker_Item**: A named entity with an associated round count, representing something the DM wants to track (e.g. a torch, a spell, an encounter timer).
- **Add_Item_Modal**: The pop-up dialog form used to create a new Round_Tracker_Item.
- **Item_Widget**: A rectangular UI element displayed in the Round_Tracker that represents a single Round_Tracker_Item.
- **Main_Window**: The top-level application window containing the tabbed interface.

## Requirements

### Requirement 1: Round Tracker Tab

**User Story:** As a DM, I want a dedicated Round Tracker tab in the application, so that I can manage round-based events separately from the Campaign Overview.

#### Acceptance Criteria

1. THE Main_Window SHALL display a "Round Tracker" tab alongside the existing "Campaign Overview" tab.
2. WHEN the "Round Tracker" tab is selected, THE Round_Tracker SHALL display its content in the central area of the window.

---

### Requirement 2: Add Item Button

**User Story:** As a DM, I want an "Add Item" button in the Round Tracker, so that I can initiate the creation of a new round tracking item.

#### Acceptance Criteria

1. THE Round_Tracker SHALL display an "Add Item" button within the tab view.
2. WHEN the user clicks the "Add Item" button, THE Round_Tracker SHALL open the Add_Item_Modal.

---

### Requirement 3: Add Item Modal Form

**User Story:** As a DM, I want a modal form with Name and Rounds fields, so that I can define a new item to track.

#### Acceptance Criteria

1. WHEN the Add_Item_Modal is opened, THE Add_Item_Modal SHALL display a "Name" text input field and a "Rounds" numeric input field.
2. WHEN the Add_Item_Modal is opened, THE Add_Item_Modal SHALL display an "Add" button and a "Cancel" button.
3. THE Add_Item_Modal SHALL accept only whole number (integer) values greater than zero in the "Rounds" field.

---

### Requirement 4: Form Validation

**User Story:** As a DM, I want the form to prevent submission when fields are blank or invalid, so that I don't accidentally create incomplete items.

#### Acceptance Criteria

1. IF the user clicks "Add" and the "Name" field is blank, THEN THE Add_Item_Modal SHALL display an error message and remain open.
2. IF the user clicks "Add" and the "Rounds" field is blank, THEN THE Add_Item_Modal SHALL display an error message and remain open.
3. IF the user clicks "Add" and the "Rounds" field does not contain a whole number greater than zero, THEN THE Add_Item_Modal SHALL display an error message and remain open.
4. WHEN the user clicks "Cancel", THE Add_Item_Modal SHALL close without creating a Round_Tracker_Item.

---

### Requirement 5: Item Widget Display

**User Story:** As a DM, I want submitted items to appear as widgets in the Round Tracker, so that I can see all tracked items at a glance.

#### Acceptance Criteria

1. WHEN the user clicks "Add" and all fields are valid, THE Round_Tracker SHALL close the Add_Item_Modal and add a new Item_Widget to the item list.
2. THE Round_Tracker SHALL display Item_Widgets in a vertically scrollable list.
3. THE Item_Widget SHALL display the Round_Tracker_Item's name on the left side of the widget.
4. THE Item_Widget SHALL display the Round_Tracker_Item's round count on the right side of the widget.
5. THE Item_Widget SHALL have a rectangular appearance.

---

### Requirement 6: State Preservation on Tab Switch

**User Story:** As a DM, I want the Round Tracker to remember its state when I switch tabs, so that I don't lose my tracked items when navigating away and back.

#### Acceptance Criteria

1. WHEN the user navigates away from the Round_Tracker tab and then returns to it, THE Round_Tracker SHALL display all Item_Widgets that were present before the tab switch.
2. WHEN the user navigates away from the Round_Tracker tab and then returns to it, THE Round_Tracker SHALL display each Item_Widget with the same name and round count it had before the tab switch.

---

### Requirement 7: Inline Name Editing

**User Story:** As a DM, I want to edit an item's name directly in the widget, so that I can rename tracked items without recreating them.

#### Acceptance Criteria

1. THE Item_Widget SHALL display the Round_Tracker_Item's name in an editable text field.
2. WHEN the user edits the name field in an Item_Widget, THE Item_Widget SHALL update the displayed name to reflect the new value.
3. IF the user clears the name field in an Item_Widget, THEN THE Item_Widget SHALL retain the previous name value.

---

### Requirement 8: Inline Round Count Editing

**User Story:** As a DM, I want to edit an item's round count directly in the widget, so that I can adjust values without recreating items.

#### Acceptance Criteria

1. THE Item_Widget SHALL display the Round_Tracker_Item's round count in an editable numeric field.
2. WHEN the user edits the round count field in an Item_Widget, THE Item_Widget SHALL update the displayed value to reflect the new input.
3. IF the user enters a value less than zero in the round count field, THEN THE Item_Widget SHALL set the round count to zero.
4. IF the user enters a non-numeric value in the round count field, THEN THE Item_Widget SHALL retain the previous round count value.

---

### Requirement 9: Decrement Button

**User Story:** As a DM, I want a '-' button to the left of the round count, so that I can quickly decrement the value by one.

#### Acceptance Criteria

1. THE Item_Widget SHALL display a circular '-' button to the left of the round count field.
2. WHEN the user clicks the '-' button, THE Item_Widget SHALL decrement the round count by one.
3. WHILE the round count is zero, THE Item_Widget SHALL NOT decrement the round count below zero when the '-' button is clicked.

---

### Requirement 10: Increment Button

**User Story:** As a DM, I want a '+' button to the right of the round count, so that I can quickly increment the value by one.

#### Acceptance Criteria

1. THE Item_Widget SHALL display a circular '+' button to the right of the round count field.
2. WHEN the user clicks the '+' button, THE Item_Widget SHALL increment the round count by one.

---

### Requirement 11: Delete Widget Button

**User Story:** As a DM, I want an 'X' button on each widget, so that I can remove items I no longer need to track.

#### Acceptance Criteria

1. THE Item_Widget SHALL display an 'X' button in the top-right corner of the widget.
2. WHEN the user clicks the 'X' button, THE Round_Tracker SHALL remove the corresponding Item_Widget from the item list.

---

### Requirement 12: Sort Button

**User Story:** As a DM, I want a 'Sort' button in the Round Tracker, so that I can automatically order all items from lowest to highest round count.

#### Acceptance Criteria

1. THE Round_Tracker SHALL display a "Sort" button within the tab view, outside of any Item_Widget.
2. WHEN the user clicks the "Sort" button, THE Round_Tracker SHALL reorder all Item_Widgets in the list from lowest to highest round count.
3. WHEN the user clicks the "Sort" button and two or more Item_Widgets share the same round count, THE Round_Tracker SHALL preserve their relative order.
