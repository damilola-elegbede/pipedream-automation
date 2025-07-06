import { axios } from "@pipedream/platform"

export default defineComponent({
  name: "Gmail to Notion Task Creator",
  description: "Creates Notion tasks from Gmail emails with retry logic and enhanced error handling",
  version: "0.1.0",
  props: {
    gmail: {
      type: "app",
      app: "gmail"
    },
    notion: {
      type: "app", 
      app: "notion"
    },
    database_id: {
      type: "string",
      label: "Notion Database ID",
      description: "The ID of the Notion database where tasks will be created"
    },
    query: {
      type: "string",
      label: "Gmail Query",
      description: "Gmail search query to filter emails",
      default: "is:unread"
    },
    max_results: {
      type: "integer",
      label: "Max Results",
      description: "Maximum number of emails to process",
      default: 10,
      min: 1,
      max: 100
    }
  },
  async run({ steps, $ }) {
    // Import the bundled Gmail to Notion module
    // This would reference the bundled code from deployment/templates/
    const { handler } = await import('./bundled/gmail_to_notion_bundled.js');
    
    // Prepare Pipedream context
    const pd = {
      inputs: {
        gmail: {
          $auth: this.gmail.$auth
        },
        notion: {
          $auth: this.notion.$auth
        },
        database_id: this.database_id,
        query: this.query,
        max_results: this.max_results
      },
      steps: steps
    };
    
    // Execute the handler with enhanced error handling and retry logic
    try {
      const result = await handler(pd);
      
      if (result.error) {
        throw new Error(`Gmail to Notion task creation failed: ${result.error}`);
      }
      
      $.export("tasks_created", result.success?.tasks_created || 0);
      $.export("processed_emails", result.success?.processed_emails || []);
      
      return result;
    } catch (error) {
      // Enhanced error reporting
      $.export("error", {
        message: error.message,
        timestamp: new Date().toISOString(),
        workflow: "gmail-to-notion"
      });
      throw error;
    }
  }
})