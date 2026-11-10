"use strict";
// The toolbar button opens the side panel beside whatever page is open.
chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true}).catch(console.error);
