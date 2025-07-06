import { axios } from "@pipedream/platform"

export default defineComponent({
  name: "Google Calendar to Notion Sync",
  description: "Syncs Google Calendar events to Notion pages with location-based filtering",
  version: "0.1.0",
  props: {
    google_calendar: {
      type: "app",
      app: "google_calendar"
    },
    notion: {
      type: "app",
      app: "notion"
    },
    database_id: {
      type: "string",
      label: "Notion Database ID",
      description: "The ID of the Notion database for calendar sync"
    },
    calendar_id: {
      type: "string", 
      label: "Calendar ID",
      description: "Google Calendar ID to sync from",
      default: "primary"
    },
    time_range_days: {
      type: "integer",
      label: "Time Range (Days)",
      description: "Number of days to look ahead for events",
      default: 7,
      min: 1,
      max: 30
    }
  },
  async run({ steps, $ }) {
    // Import the bundled Calendar to Notion module
    const { handler } = await import('./bundled/calendar_to_notion_bundled.js');
    
    // Calculate time range
    const now = new Date();
    const timeMin = now.toISOString();
    const timeMax = new Date(now.getTime() + (this.time_range_days * 24 * 60 * 60 * 1000)).toISOString();
    
    // Prepare Pipedream context
    const pd = {
      inputs: {
        google_calendar: {
          $auth: this.google_calendar.$auth
        },
        notion: {
          $auth: this.notion.$auth
        },
        database_id: this.database_id,
        calendar_id: this.calendar_id,
        time_min: timeMin,
        time_max: timeMax
      },
      steps: steps
    };
    
    // Execute with enhanced error handling
    try {
      const result = await handler(pd);
      
      if (result.error) {
        throw new Error(`Calendar to Notion sync failed: ${result.error}`);
      }
      
      $.export("events_processed", result.success?.events_processed || 0);
      $.export("notion_pages_created", result.success?.notion_pages_created || 0);
      $.export("notion_pages_updated", result.success?.notion_pages_updated || 0);
      $.export("sync_timestamp", new Date().toISOString());
      
      return result;
    } catch (error) {
      $.export("error", {
        message: error.message,
        timestamp: new Date().toISOString(),
        workflow: "gcal-to-notion",
        calendar_id: this.calendar_id,
        time_range: `${timeMin} to ${timeMax}`
      });
      throw error;
    }
  }
})