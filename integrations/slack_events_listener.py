"""
Slack Events API and Socket Mode Listener for AI Gatekeeper System
Handles real-time Slack events with proper authentication and verification
"""

import os
import json
import hmac
import hashlib
import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from flask import Flask, request, jsonify
from threading import Thread

# Slack SDK imports
try:
    from slack_sdk import WebClient
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.request import SocketModeRequest
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    logging.warning("Slack SDK not available. Install with: pip install slack-sdk slack-bolt")

class SlackEventsListener:
    """
    Enhanced Slack Events API and Socket Mode listener with proper authentication.
    """
    
    def __init__(self, bot_token: str, app_token: str = None, signing_secret: str = None,
                 support_processor=None, flask_app: Flask = None):
        """
        Initialize Slack Events listener.
        
        Args:
            bot_token: Slack bot token (xoxb-...)
            app_token: Slack app token for Socket Mode (xapp-...)
            signing_secret: Slack signing secret for request verification
            support_processor: AI Gatekeeper support processor
            flask_app: Flask app for HTTP events endpoint
        """
        if not SLACK_SDK_AVAILABLE:
            raise ImportError("Slack SDK not available. Install with: pip install slack-sdk slack-bolt")
        
        self.bot_token = bot_token
        self.app_token = app_token
        self.signing_secret = signing_secret
        self.support_processor = support_processor
        self.flask_app = flask_app
        
        # Initialize Slack clients
        self.web_client = WebClient(token=bot_token)
        self.socket_client = None
        self.bolt_app = None
        
        # Event handlers
        self.event_handlers: Dict[str, Callable] = {}
        self.command_handlers: Dict[str, Callable] = {}
        self.action_handlers: Dict[str, Callable] = {}
        
        # Configuration
        self.support_channels = self._get_support_channels()
        self.bot_user_id = None
        
        # Initialize components
        self._setup_bolt_app()
        self._register_default_handlers()
        
        # Get bot user ID
        self._get_bot_user_id()
        
        logging.info("Slack Events Listener initialized")
    
    def _get_support_channels(self) -> set:
        """Get configured support channels."""
        channels = os.getenv('SLACK_SUPPORT_CHANNELS', 'support,help,it-support').split(',')
        return {ch.strip() for ch in channels if ch.strip()}
    
    def _setup_bolt_app(self):
        """Setup Slack Bolt app with proper configuration."""
        if self.app_token:
            # Socket Mode configuration
            self.bolt_app = App(
                token=self.bot_token,
                signing_secret=self.signing_secret
            )
            
            # Initialize socket mode client
            self.socket_client = SocketModeClient(
                app_token=self.app_token,
                web_client=self.web_client
            )
        else:
            # HTTP mode configuration
            self.bolt_app = App(
                token=self.bot_token,
                signing_secret=self.signing_secret
            )
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        if not self.bolt_app:
            return
        
        # Message events
        @self.bolt_app.event("app_mention")
        def handle_app_mention(event, say, client):
            asyncio.run(self._handle_app_mention(event, say, client))
        
        @self.bolt_app.event("message")
        def handle_message(event, say, client):
            asyncio.run(self._handle_message(event, say, client))
        
        # Slash commands
        @self.bolt_app.command("/ai-support")
        def handle_support_command(ack, respond, command, client):
            asyncio.run(self._handle_support_command(ack, respond, command, client))
        
        # Interactive components
        @self.bolt_app.action("feedback_rating")
        def handle_feedback_rating(ack, body, client):
            asyncio.run(self._handle_feedback_rating(ack, body, client))
        
        @self.bolt_app.action("escalate_request")
        def handle_escalation_request(ack, body, client):
            asyncio.run(self._handle_escalation_request(ack, body, client))
    
    def _get_bot_user_id(self):
        """Get bot user ID for message filtering."""
        try:
            response = self.web_client.auth_test()
            self.bot_user_id = response.get('user_id')
            logging.info(f"Bot user ID: {self.bot_user_id}")
        except Exception as e:
            logging.error(f"Failed to get bot user ID: {e}")
    
    async def _handle_app_mention(self, event, say, client):
        """Handle app mention events."""
        try:
            user_id = event.get('user')
            text = event.get('text', '')
            channel = event.get('channel')
            
            # Remove bot mention from text
            if self.bot_user_id:
                text = text.replace(f'<@{self.bot_user_id}>', '').strip()
            
            # Process support request
            if self.support_processor:
                user_context = await self._get_user_context(user_id, channel)
                
                # Process the request
                ticket = await self.support_processor.process_support_request(
                    text, user_context
                )
                
                # Send response based on resolution
                if ticket.status == 'ai_auto':
                    await self._send_automated_solution(say, ticket)
                else:
                    await self._send_escalation_notification(say, ticket)
            else:
                await say("AI Gatekeeper support processor is not available.")
                
        except Exception as e:
            logging.error(f"Error handling app mention: {e}")
            await say("Sorry, I encountered an error processing your request.")
    
    async def _handle_message(self, event, say, client):
        """Handle direct message events."""
        try:
            # Only process direct messages or messages in support channels
            channel = event.get('channel')
            channel_type = event.get('channel_type')
            user_id = event.get('user')
            
            # Skip bot messages
            if user_id == self.bot_user_id:
                return
            
            # Skip messages with subtypes (like bot messages)
            if event.get('subtype'):
                return
            
            # Check if it's a DM or support channel
            is_dm = channel_type == 'im'
            is_support_channel = await self._is_support_channel(channel, client)
            
            if is_dm or is_support_channel:
                text = event.get('text', '')
                
                # Process support request
                if self.support_processor:
                    user_context = await self._get_user_context(user_id, channel)
                    
                    # Process the request
                    ticket = await self.support_processor.process_support_request(
                        text, user_context
                    )
                    
                    # Send response based on resolution
                    if ticket.status == 'ai_auto':
                        await self._send_automated_solution(say, ticket)
                    else:
                        await self._send_escalation_notification(say, ticket)
                        
        except Exception as e:
            logging.error(f"Error handling message: {e}")
    
    async def _handle_support_command(self, ack, respond, command, client):
        """Handle /ai-support slash command."""
        try:
            await ack()
            
            text = command.get('text', '').strip()
            user_id = command.get('user_id')
            channel_id = command.get('channel_id')
            
            if not text:
                await respond({
                    "response_type": "ephemeral",
                    "text": "Please provide a description of your issue. Example: `/ai-support My application crashes when I try to save files`"
                })
                return
            
            # Process support request
            if self.support_processor:
                user_context = await self._get_user_context(user_id, channel_id)
                
                # Process the request
                ticket = await self.support_processor.process_support_request(
                    text, user_context
                )
                
                # Send response based on resolution
                if ticket.status == 'ai_auto':
                    response = self._format_automated_solution_response(ticket)
                else:
                    response = self._format_escalation_response(ticket)
                
                await respond(response)
            else:
                await respond({
                    "response_type": "ephemeral",
                    "text": "AI Gatekeeper support processor is not available."
                })
                
        except Exception as e:
            logging.error(f"Error handling support command: {e}")
            await respond({
                "response_type": "ephemeral",
                "text": "Sorry, I encountered an error processing your request."
            })
    
    async def _handle_feedback_rating(self, ack, body, client):
        """Handle feedback rating button clicks."""
        try:
            await ack()
            
            user_id = body.get('user', {}).get('id')
            action_value = body.get('actions', [{}])[0].get('value')
            
            if action_value:
                # Parse rating and ticket ID
                rating_data = json.loads(action_value)
                rating = rating_data.get('rating')
                ticket_id = rating_data.get('ticket_id')
                
                # Submit feedback
                if self.support_processor:
                    # Call feedback endpoint
                    feedback_result = await self._submit_feedback(
                        ticket_id, rating, user_id
                    )
                    
                    # Update message with feedback confirmation
                    await self._update_message_with_feedback(
                        client, body, rating, feedback_result
                    )
            
        except Exception as e:
            logging.error(f"Error handling feedback rating: {e}")
    
    async def _handle_escalation_request(self, ack, body, client):
        """Handle escalation request button clicks."""
        try:
            await ack()
            
            user_id = body.get('user', {}).get('id')
            action_value = body.get('actions', [{}])[0].get('value')
            
            if action_value:
                # Parse ticket ID
                escalation_data = json.loads(action_value)
                ticket_id = escalation_data.get('ticket_id')
                
                # Escalate to human
                if self.support_processor:
                    # Call handoff endpoint
                    handoff_result = await self._handoff_to_human(
                        ticket_id, "User requested escalation", user_id
                    )
                    
                    # Update message with escalation confirmation
                    await self._update_message_with_escalation(
                        client, body, handoff_result
                    )
            
        except Exception as e:
            logging.error(f"Error handling escalation request: {e}")
    
    async def _get_user_context(self, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Get user context for support processing."""
        try:
            # Get user info
            user_info = await self.web_client.users_info(user=user_id)
            user_data = user_info.get('user', {})
            
            # Get channel info
            channel_info = await self.web_client.conversations_info(channel=channel_id)
            channel_data = channel_info.get('channel', {})
            
            return {
                'user_id': user_id,
                'user_name': user_data.get('name', 'Unknown'),
                'user_email': user_data.get('profile', {}).get('email'),
                'channel_id': channel_id,
                'channel_name': channel_data.get('name', 'Unknown'),
                'source': 'slack',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error getting user context: {e}")
            return {
                'user_id': user_id,
                'channel_id': channel_id,
                'source': 'slack',
                'timestamp': datetime.now().isoformat()
            }
    
    async def _is_support_channel(self, channel_id: str, client) -> bool:
        """Check if channel is a support channel."""
        try:
            channel_info = await client.conversations_info(channel=channel_id)
            channel_name = channel_info.get('channel', {}).get('name', '').lower()
            
            return any(pattern in channel_name for pattern in self.support_channels)
            
        except Exception as e:
            logging.error(f"Error checking support channel: {e}")
            return False
    
    async def _send_automated_solution(self, say, ticket):
        """Send automated solution message."""
        try:
            solution_data = ticket.triage_analysis.get('solution', {})
            blocks = self._create_solution_blocks(ticket, solution_data)
            
            await say(blocks=blocks)
            
        except Exception as e:
            logging.error(f"Error sending automated solution: {e}")
    
    async def _send_escalation_notification(self, say, ticket):
        """Send escalation notification message."""
        try:
            blocks = self._create_escalation_blocks(ticket)
            await say(blocks=blocks)
            
        except Exception as e:
            logging.error(f"Error sending escalation notification: {e}")
    
    def _create_solution_blocks(self, ticket, solution_data) -> List[Dict[str, Any]]:
        """Create Slack blocks for automated solution."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🤖 AI Support Resolution"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Solution for your request:*\n{solution_data.get('summary', 'Solution generated')}"
                }
            }
        ]
        
        # Add steps if available
        steps = solution_data.get('steps', [])
        if steps:
            steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps[:5])])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Steps:*\n{steps_text}"
                }
            })
        
        # Add metadata
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Confidence:* {ticket.confidence_score:.0%} | *Estimated Time:* {solution_data.get('estimated_time', 'Unknown')}"
            }
        })
        
        # Add feedback buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👍 Helpful"},
                    "style": "primary",
                    "action_id": "feedback_rating",
                    "value": json.dumps({"rating": 5, "ticket_id": str(ticket.id)})
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👎 Not Helpful"},
                    "style": "danger",
                    "action_id": "feedback_rating",
                    "value": json.dumps({"rating": 1, "ticket_id": str(ticket.id)})
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🆘 Escalate"},
                    "action_id": "escalate_request",
                    "value": json.dumps({"ticket_id": str(ticket.id)})
                }
            ]
        })
        
        return blocks
    
    def _create_escalation_blocks(self, ticket) -> List[Dict[str, Any]]:
        """Create Slack blocks for escalation notification."""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👨‍💻 Escalated to Human Expert"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Your request has been escalated to our support team.*\n\n*Issue:* {ticket.message[:100]}{'...' if len(ticket.message) > 100 else ''}\n*Priority:* {ticket.priority}\n*Request ID:* {ticket.id}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Analysis:*\n• Confidence: {ticket.confidence_score:.0%}\n• Risk Level: {ticket.risk_score:.0%}\n• Reason: {ticket.escalation_reason or 'Requires human expertise'}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "You'll be contacted shortly by our support team."
                }
            }
        ]
    
    def _format_automated_solution_response(self, ticket) -> Dict[str, Any]:
        """Format automated solution response for slash command."""
        solution_data = ticket.triage_analysis.get('solution', {})
        
        return {
            "response_type": "ephemeral",
            "blocks": self._create_solution_blocks(ticket, solution_data)
        }
    
    def _format_escalation_response(self, ticket) -> Dict[str, Any]:
        """Format escalation response for slash command."""
        return {
            "response_type": "ephemeral",
            "blocks": self._create_escalation_blocks(ticket)
        }
    
    async def _submit_feedback(self, ticket_id: str, rating: int, user_id: str) -> Dict[str, Any]:
        """Submit feedback to the system."""
        try:
            # This would call the feedback API endpoint
            # For now, return a placeholder
            return {
                "success": True,
                "message": "Feedback submitted successfully"
            }
        except Exception as e:
            logging.error(f"Error submitting feedback: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handoff_to_human(self, ticket_id: str, reason: str, user_id: str) -> Dict[str, Any]:
        """Handoff ticket to human expert."""
        try:
            # This would call the handoff API endpoint
            # For now, return a placeholder
            return {
                "success": True,
                "message": "Ticket escalated to human expert"
            }
        except Exception as e:
            logging.error(f"Error in handoff: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_message_with_feedback(self, client, body, rating: int, feedback_result: Dict[str, Any]):
        """Update message with feedback confirmation."""
        try:
            # Replace action buttons with feedback confirmation
            updated_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ Thank you for your feedback! (Rating: {rating}/5)"
                    }
                }
            ]
            
            # Update the message
            await client.chat_update(
                channel=body.get('channel', {}).get('id'),
                ts=body.get('message', {}).get('ts'),
                blocks=updated_blocks
            )
            
        except Exception as e:
            logging.error(f"Error updating message with feedback: {e}")
    
    async def _update_message_with_escalation(self, client, body, handoff_result: Dict[str, Any]):
        """Update message with escalation confirmation."""
        try:
            # Replace action buttons with escalation confirmation
            updated_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ Your request has been escalated to our support team. You'll hear from us soon!"
                    }
                }
            ]
            
            # Update the message
            await client.chat_update(
                channel=body.get('channel', {}).get('id'),
                ts=body.get('message', {}).get('ts'),
                blocks=updated_blocks
            )
            
        except Exception as e:
            logging.error(f"Error updating message with escalation: {e}")
    
    def verify_slack_signature(self, request_body: str, timestamp: str, signature: str) -> bool:
        """Verify Slack request signature."""
        if not self.signing_secret:
            return False
        
        # Check timestamp to prevent replay attacks
        if abs(time.time() - int(timestamp)) > 60 * 5:  # 5 minutes
            return False
        
        # Create signature
        sig_basestring = f'v0:{timestamp}:{request_body}'
        expected_signature = 'v0=' + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def start_socket_mode(self):
        """Start Socket Mode listener."""
        if not self.socket_client:
            raise ValueError("Socket Mode not configured. Provide app_token.")
        
        # Create socket mode handler
        handler = SocketModeHandler(self.bolt_app, self.socket_client)
        
        # Start the handler
        handler.start()
        logging.info("Slack Socket Mode listener started")
    
    def setup_http_events(self):
        """Setup HTTP events endpoint on Flask app."""
        if not self.flask_app:
            raise ValueError("Flask app not provided for HTTP events")
        
        @self.flask_app.route('/slack/events', methods=['POST'])
        def slack_events():
            # Verify request
            if not self.verify_slack_signature(
                request.get_data(as_text=True),
                request.headers.get('X-Slack-Request-Timestamp', ''),
                request.headers.get('X-Slack-Signature', '')
            ):
                return jsonify({'error': 'Invalid signature'}), 401
            
            # Handle URL verification
            if request.json.get('type') == 'url_verification':
                return jsonify({'challenge': request.json.get('challenge')})
            
            # Process event
            try:
                event_data = request.json
                event_type = event_data.get('event', {}).get('type')
                
                if event_type in ['message', 'app_mention']:
                    # Process asynchronously
                    Thread(target=self._process_event_async, args=(event_data,)).start()
                
                return jsonify({'ok': True})
                
            except Exception as e:
                logging.error(f"Error processing Slack event: {e}")
                return jsonify({'error': 'Internal error'}), 500
        
        logging.info("Slack HTTP events endpoint configured")
    
    def _process_event_async(self, event_data: Dict[str, Any]):
        """Process Slack event asynchronously."""
        try:
            # This would process the event using the bolt app
            # For now, just log it
            logging.info(f"Processing Slack event: {event_data.get('event', {}).get('type')}")
        except Exception as e:
            logging.error(f"Error processing event async: {e}")


def create_slack_listener(support_processor=None, flask_app: Flask = None) -> Optional[SlackEventsListener]:
    """Create and configure Slack events listener."""
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    app_token = os.getenv('SLACK_APP_TOKEN')  
    signing_secret = os.getenv('SLACK_SIGNING_SECRET')
    
    if not bot_token:
        logging.warning("SLACK_BOT_TOKEN not configured. Slack integration disabled.")
        return None
    
    if not signing_secret:
        logging.warning("SLACK_SIGNING_SECRET not configured. Request verification disabled.")
    
    try:
        listener = SlackEventsListener(
            bot_token=bot_token,
            app_token=app_token,
            signing_secret=signing_secret,
            support_processor=support_processor,
            flask_app=flask_app
        )
        
        # Setup HTTP events if Flask app provided
        if flask_app:
            listener.setup_http_events()
        
        # Start Socket Mode if app token provided
        if app_token:
            listener.start_socket_mode()
        
        return listener
        
    except Exception as e:
        logging.error(f"Failed to create Slack listener: {e}")
        return None