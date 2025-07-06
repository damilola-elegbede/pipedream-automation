import { axios } from "@pipedream/platform"

export default defineComponent({
  name: "Notion to Google Calendar Event Creator",
  description: "Creates or updates Google Calendar events from Notion tasks with automatic retry",
  version: "0.1.0",
  props: {
    notion: {
      type: "app",
      app: "notion"
    },
    google_calendar: {
      type: "app",
      app: "google_calendar"
    },
    calendar_id: {
      type: "string",
      label: "Calendar ID",
      description: "Google Calendar ID (use 'primary' for main calendar)",
      default: "primary"
    },
    task: {
      type: "object",
      label: "Notion Task",
      description: "Notion task object from previous step"
    }
  },
  async run({ steps, $ }) {
    // Import the bundled Notion to Calendar module
    const { handler } = await import('./bundled/notion_to_gcal_bundled.js');
    
    // Prepare Pipedream context
    const pd = {
      task: this.task || steps.trigger?.event,
      calendar_auth: this.google_calendar.$auth.oauth_access_token,
      calendar_id: this.calendar_id,
      inputs: {
        notion: {
          $auth: this.notion.$auth
        },
        google_calendar: {
          $auth: this.google_calendar.$auth
        }
      },
      steps: steps
    };
    
    // Execute with enhanced error handling
    try {
      const result = await handler(pd);
      
      if (result.error) {
        throw new Error(`Notion to Calendar sync failed: ${result.error}`);
      }
      
      $.export("event_id", result.success?.event_id);
      $.export("event_url", result.success?.event_url);
      $.export("sync_type", result.success?.event_id ? "updated" : "created");
      
      return result;
    } catch (error) {
      $.export("error", {
        message: error.message,
        timestamp: new Date().toISOString(),
        workflow: "notion-to-gcal",
        task_id: this.task?.id
      });
      throw error;
    }
  }
})