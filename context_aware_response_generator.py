#!/usr/bin/env python3
"""
Context-Aware Response Generator - POC Implementation
Generates comprehensive, intelligent responses like modern AI chat systems.
Features:
- Rich semantic context building
- Multi-faceted response generation
- Business intelligence insights
- Actionable recommendations
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import re
from enum import Enum

logger = logging.getLogger(__name__)

class ResponseType(Enum):
    """Types of responses that can be generated."""
    DIRECT_ANSWER = "direct_answer"
    ANALYSIS = "analysis"
    RECOMMENDATION = "recommendation"
    WARNING = "warning"
    FOLLOW_UP = "follow_up"

@dataclass
class DataInsight:
    """Represents an insight extracted from data."""
    type: str
    message: str
    confidence: float
    source_tools: List[str]
    business_impact: str = ""
    urgency: str = "normal"  # low, normal, high, critical

@dataclass
class Recommendation:
    """Represents an actionable recommendation."""
    action: str
    reason: str
    priority: str  # low, medium, high, critical
    timeline: str  # immediate, short-term, long-term
    impact: str
    tools_required: List[str] = None
    
    def __post_init__(self):
        if self.tools_required is None:
            self.tools_required = []

@dataclass
class ContextualResponse:
    """Complete contextual response with multiple facets."""
    direct_answer: str
    insights: List[DataInsight]
    recommendations: List[Recommendation]
    business_context: str
    follow_up_questions: List[str]
    warnings: List[str]
    data_sources: List[Dict[str, Any]]
    confidence_score: float
    response_timestamp: str = None
    
    def __post_init__(self):
        if self.response_timestamp is None:
            self.response_timestamp = datetime.now().isoformat()

class SemanticContextBuilder:
    """Builds rich semantic context from tool results and schemas."""
    
    def __init__(self):
        self.financial_entities = {
            'payment', 'account', 'balance', 'transaction', 'transfer',
            'settlement', 'security', 'portfolio', 'position', 'trade'
        }
        
        self.temporal_keywords = {
            'pending', 'completed', 'failed', 'processing', 'scheduled',
            'overdue', 'upcoming', 'recent', 'historical'
        }
        
        self.risk_indicators = {
            'failed', 'rejected', 'overdue', 'insufficient', 'declined',
            'suspended', 'blocked', 'frozen', 'exceeded'
        }
    
    def build_context(self, tool_results: List[Dict], schemas: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Build comprehensive semantic context from tool results."""
        
        context = {
            "entities": self._extract_entities(tool_results, schemas),
            "relationships": self._find_relationships(tool_results),
            "temporal_patterns": self._analyze_temporal_patterns(tool_results),
            "risk_indicators": self._detect_risks(tool_results),
            "business_metrics": self._calculate_metrics(tool_results),
            "data_quality": self._assess_data_quality(tool_results),
            "user_intent": self._analyze_user_intent(user_query),
            "domain_knowledge": self._extract_domain_knowledge(schemas)
        }
        
        return context
    
    def _extract_entities(self, tool_results: List[Dict], schemas: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Extract business entities from tool results."""
        entities = {
            "financial_accounts": [],
            "payments": [],
            "transactions": [],
            "securities": [],
            "messages": [],
            "users": [],
            "amounts": [],
            "dates": []
        }
        
        for result in tool_results:
            if not result.get('success'):
                continue
                
            data = result.get('result', {})
            tool_name = result.get('tool_name', '')
            
            # Extract based on tool type and data patterns
            if 'account' in tool_name.lower():
                entities["financial_accounts"].extend(self._extract_accounts(data))
            elif 'payment' in tool_name.lower():
                entities["payments"].extend(self._extract_payments(data))
            elif 'transaction' in tool_name.lower():
                entities["transactions"].extend(self._extract_transactions(data))
            elif 'securities' in tool_name.lower() or 'portfolio' in tool_name.lower():
                entities["securities"].extend(self._extract_securities(data))
            elif 'message' in tool_name.lower() or 'mailbox' in tool_name.lower():
                entities["messages"].extend(self._extract_messages(data))
            
            # Extract cross-cutting concerns
            entities["amounts"].extend(self._extract_amounts(data))
            entities["dates"].extend(self._extract_dates(data))
        
        return entities
    
    def _extract_accounts(self, data: Any) -> List[Dict]:
        """Extract account information."""
        accounts = []
        
        if isinstance(data, dict):
            if 'accounts' in data:
                accounts.extend(data['accounts'])
            elif 'account' in data:
                accounts.append(data['account'])
            elif 'accountNumber' in data or 'balance' in data:
                accounts.append(data)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and ('accountNumber' in item or 'balance' in item):
                    accounts.append(item)
        
        # Enrich with metadata
        for account in accounts:
            account['entity_type'] = 'financial_account'
            account['extracted_at'] = datetime.now().isoformat()
        
        return accounts
    
    def _extract_payments(self, data: Any) -> List[Dict]:
        """Extract payment information."""
        payments = []
        
        if isinstance(data, dict):
            if 'payments' in data:
                payments.extend(data['payments'])
            elif 'payment' in data:
                payments.append(data['payment'])
            elif 'amount' in data and 'status' in data:
                payments.append(data)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'amount' in item:
                    payments.append(item)
        
        # Enrich with metadata
        for payment in payments:
            payment['entity_type'] = 'payment'
            payment['extracted_at'] = datetime.now().isoformat()
            
            # Add urgency assessment
            status = payment.get('status', '').lower()
            if status in ['failed', 'rejected', 'overdue']:
                payment['urgency'] = 'high'
            elif status in ['pending', 'processing']:
                payment['urgency'] = 'medium'
            else:
                payment['urgency'] = 'low'
        
        return payments
    
    def _extract_transactions(self, data: Any) -> List[Dict]:
        """Extract transaction information."""
        transactions = []
        
        if isinstance(data, dict):
            if 'transactions' in data:
                transactions.extend(data['transactions'])
            elif 'transaction' in data:
                transactions.append(data['transaction'])
        elif isinstance(data, list):
            transactions.extend([item for item in data if isinstance(item, dict)])
        
        # Enrich with metadata
        for txn in transactions:
            txn['entity_type'] = 'transaction'
            txn['extracted_at'] = datetime.now().isoformat()
        
        return transactions
    
    def _extract_securities(self, data: Any) -> List[Dict]:
        """Extract securities information."""
        securities = []
        
        if isinstance(data, dict):
            if 'securities' in data:
                securities.extend(data['securities'])
            elif 'positions' in data:
                securities.extend(data['positions'])
        elif isinstance(data, list):
            securities.extend([item for item in data if isinstance(item, dict)])
        
        # Enrich with metadata
        for security in securities:
            security['entity_type'] = 'security'
            security['extracted_at'] = datetime.now().isoformat()
        
        return securities
    
    def _extract_messages(self, data: Any) -> List[Dict]:
        """Extract message information."""
        messages = []
        
        if isinstance(data, dict):
            if 'messages' in data:
                messages.extend(data['messages'])
            elif 'message' in data:
                messages.append(data['message'])
        elif isinstance(data, list):
            messages.extend([item for item in data if isinstance(item, dict)])
        
        # Enrich with metadata
        for msg in messages:
            msg['entity_type'] = 'message'
            msg['extracted_at'] = datetime.now().isoformat()
        
        return messages
    
    def _extract_amounts(self, data: Any) -> List[Dict]:
        """Extract monetary amounts."""
        amounts = []
        
        def extract_from_dict(d: Dict, path: str = ""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                
                if key.lower() in ['amount', 'balance', 'value', 'price', 'total']:
                    if isinstance(value, (int, float)):
                        amounts.append({
                            'value': value,
                            'field': key,
                            'path': current_path,
                            'currency': d.get('currency', 'USD'),
                            'entity_type': 'amount'
                        })
                elif isinstance(value, dict):
                    extract_from_dict(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            extract_from_dict(item, f"{current_path}[{i}]")
        
        if isinstance(data, dict):
            extract_from_dict(data)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    extract_from_dict(item, f"[{i}]")
        
        return amounts
    
    def _extract_dates(self, data: Any) -> List[Dict]:
        """Extract date/time information."""
        dates = []
        
        def extract_from_dict(d: Dict, path: str = ""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                
                if any(keyword in key.lower() for keyword in ['date', 'time', 'created', 'updated', 'due', 'expires']):
                    if isinstance(value, str):
                        dates.append({
                            'value': value,
                            'field': key,
                            'path': current_path,
                            'entity_type': 'date'
                        })
                elif isinstance(value, dict):
                    extract_from_dict(value, current_path)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            extract_from_dict(item, f"{current_path}[{i}]")
        
        if isinstance(data, dict):
            extract_from_dict(data)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    extract_from_dict(item, f"[{i}]")
        
        return dates
    
    def _find_relationships(self, tool_results: List[Dict]) -> List[Dict]:
        """Find relationships between entities."""
        relationships = []
        
        # For POC, implement basic account-payment relationships
        accounts = []
        payments = []
        
        for result in tool_results:
            if not result.get('success'):
                continue
                
            data = result.get('result', {})
            tool_name = result.get('tool_name', '')
            
            if 'account' in tool_name.lower():
                accounts.extend(self._extract_accounts(data))
            elif 'payment' in tool_name.lower():
                payments.extend(self._extract_payments(data))
        
        # Find account-payment relationships
        for payment in payments:
            payment_account = payment.get('accountNumber') or payment.get('account')
            if payment_account:
                for account in accounts:
                    account_number = account.get('accountNumber') or account.get('account')
                    if account_number == payment_account:
                        relationships.append({
                            'type': 'account_payment',
                            'source': account,
                            'target': payment,
                            'relationship': f"Payment from account {account_number}"
                        })
        
        return relationships
    
    def _analyze_temporal_patterns(self, tool_results: List[Dict]) -> Dict[str, Any]:
        """Analyze temporal patterns in the data."""
        patterns = {
            'recent_activity': [],
            'upcoming_deadlines': [],
            'overdue_items': [],
            'trends': []
        }
        
        now = datetime.now()
        
        for result in tool_results:
            if not result.get('success'):
                continue
                
            data = result.get('result', {})
            dates = self._extract_dates(data)
            
            for date_info in dates:
                try:
                    date_value = datetime.fromisoformat(date_info['value'].replace('Z', '+00:00'))
                    field_name = date_info['field'].lower()
                    
                    # Recent activity (last 7 days)
                    if (now - date_value).days <= 7 and 'created' in field_name:
                        patterns['recent_activity'].append({
                            'date': date_value.isoformat(),
                            'type': field_name,
                            'data': date_info
                        })
                    
                    # Upcoming deadlines (next 30 days)
                    if date_value > now and (date_value - now).days <= 30 and 'due' in field_name:
                        patterns['upcoming_deadlines'].append({
                            'date': date_value.isoformat(),
                            'days_until': (date_value - now).days,
                            'data': date_info
                        })
                    
                    # Overdue items
                    if date_value < now and 'due' in field_name:
                        patterns['overdue_items'].append({
                            'date': date_value.isoformat(),
                            'days_overdue': (now - date_value).days,
                            'data': date_info
                        })
                        
                except (ValueError, TypeError):
                    continue
        
        return patterns
    
    def _detect_risks(self, tool_results: List[Dict]) -> List[Dict]:
        """Detect risk indicators in the data."""
        risks = []
        
        for result in tool_results:
            if not result.get('success'):
                continue
                
            data = result.get('result', {})
            
            # Look for risk keywords in status fields
            def scan_for_risks(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        
                        if isinstance(value, str) and any(risk in value.lower() for risk in self.risk_indicators):
                            risks.append({
                                'type': 'status_risk',
                                'path': current_path,
                                'value': value,
                                'severity': self._assess_risk_severity(value),
                                'source_tool': result.get('tool_name')
                            })
                        elif isinstance(value, (dict, list)):
                            scan_for_risks(value, current_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        scan_for_risks(item, f"{path}[{i}]")
            
            scan_for_risks(data)
        
        return risks
    
    def _assess_risk_severity(self, status_value: str) -> str:
        """Assess the severity of a risk indicator."""
        high_risk = ['failed', 'rejected', 'suspended', 'blocked', 'frozen']
        medium_risk = ['overdue', 'declined', 'exceeded']
        
        status_lower = status_value.lower()
        
        if any(risk in status_lower for risk in high_risk):
            return 'high'
        elif any(risk in status_lower for risk in medium_risk):
            return 'medium'
        else:
            return 'low'
    
    def _calculate_metrics(self, tool_results: List[Dict]) -> Dict[str, Any]:
        """Calculate business metrics from the data."""
        metrics = {
            'total_amounts': {},
            'status_counts': {},
            'success_rate': 0.0,
            'data_freshness': 'unknown'
        }
        
        # Calculate totals by currency
        for result in tool_results:
            if not result.get('success'):
                continue
                
            amounts = self._extract_amounts(result.get('result', {}))
            for amount in amounts:
                currency = amount.get('currency', 'USD')
                value = amount.get('value', 0)
                
                if currency not in metrics['total_amounts']:
                    metrics['total_amounts'][currency] = 0
                metrics['total_amounts'][currency] += value
        
        # Calculate success rate of tool calls
        total_tools = len(tool_results)
        successful_tools = sum(1 for r in tool_results if r.get('success'))
        metrics['success_rate'] = successful_tools / total_tools if total_tools > 0 else 0
        
        return metrics
    
    def _assess_data_quality(self, tool_results: List[Dict]) -> Dict[str, Any]:
        """Assess the quality of the retrieved data."""
        quality = {
            'completeness': 0.0,
            'consistency': 0.0,
            'timeliness': 'unknown',
            'issues': []
        }
        
        successful_results = [r for r in tool_results if r.get('success')]
        quality['completeness'] = len(successful_results) / len(tool_results) if tool_results else 0
        
        # Check for consistency issues
        if len(successful_results) > 1:
            # Simple consistency check - look for conflicting currency codes or date formats
            currencies = set()
            date_formats = set()
            
            for result in successful_results:
                amounts = self._extract_amounts(result.get('result', {}))
                dates = self._extract_dates(result.get('result', {}))
                
                currencies.update(amount.get('currency', 'USD') for amount in amounts)
                date_formats.update(self._detect_date_format(date['value']) for date in dates)
            
            quality['consistency'] = 1.0 if len(currencies) <= 2 and len(date_formats) <= 2 else 0.5
        
        return quality
    
    def _detect_date_format(self, date_str: str) -> str:
        """Detect the format of a date string."""
        if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', date_str):
            return 'iso8601'
        elif re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return 'date_only'
        else:
            return 'other'
    
    def _analyze_user_intent(self, user_query: str) -> Dict[str, Any]:
        """Analyze user intent from the query."""
        intent = {
            'primary_action': 'unknown',
            'entities_mentioned': [],
            'temporal_context': None,
            'urgency': 'normal'
        }
        
        query_lower = user_query.lower()
        
        # Detect primary action
        if any(word in query_lower for word in ['show', 'list', 'get', 'display']):
            intent['primary_action'] = 'retrieve'
        elif any(word in query_lower for word in ['pay', 'transfer', 'send']):
            intent['primary_action'] = 'execute'
        elif any(word in query_lower for word in ['analyze', 'compare', 'calculate']):
            intent['primary_action'] = 'analyze'
        elif any(word in query_lower for word in ['status', 'check']):
            intent['primary_action'] = 'status_check'
        
        # Detect mentioned entities
        for entity in self.financial_entities:
            if entity in query_lower:
                intent['entities_mentioned'].append(entity)
        
        # Detect temporal context
        if any(word in query_lower for word in ['pending', 'upcoming', 'today']):
            intent['temporal_context'] = 'immediate'
        elif any(word in query_lower for word in ['recent', 'latest', 'last']):
            intent['temporal_context'] = 'recent'
        elif any(word in query_lower for word in ['future', 'next', 'upcoming']):
            intent['temporal_context'] = 'future'
        
        # Detect urgency
        if any(word in query_lower for word in ['urgent', 'immediate', 'asap', 'critical']):
            intent['urgency'] = 'high'
        elif any(word in query_lower for word in ['soon', 'quickly']):
            intent['urgency'] = 'medium'
        
        return intent
    
    def _extract_domain_knowledge(self, schemas: Dict[str, Any]) -> Dict[str, Any]:
        """Extract domain knowledge from schemas."""
        knowledge = {
            'business_rules': [],
            'validation_constraints': [],
            'entity_relationships': [],
            'data_types': {}
        }
        
        for tool_name, schema in schemas.items():
            # Extract business rules from descriptions and constraints
            if isinstance(schema, dict):
                properties = schema.get('properties', {})
                for prop_name, prop_schema in properties.items():
                    if isinstance(prop_schema, dict):
                        # Extract validation constraints
                        constraints = {}
                        for constraint in ['minimum', 'maximum', 'pattern', 'enum']:
                            if constraint in prop_schema:
                                constraints[constraint] = prop_schema[constraint]
                        
                        if constraints:
                            knowledge['validation_constraints'].append({
                                'tool': tool_name,
                                'property': prop_name,
                                'constraints': constraints
                            })
                        
                        # Extract data types
                        if 'type' in prop_schema:
                            knowledge['data_types'][f"{tool_name}.{prop_name}"] = prop_schema['type']
        
        return knowledge


class ContextAwareResponseGenerator:
    """Generates comprehensive, intelligent responses using semantic context."""
    
    def __init__(self):
        self.context_builder = SemanticContextBuilder()
        
        # Response templates for different scenarios (placeholder for future implementation)
        self.templates = {
            'financial_summary': 'financial_summary',
            'status_update': 'status_update', 
            'analysis_report': 'analysis_report',
            'action_required': 'action_required'
        }
    
    async def generate_response(self, user_query: str, tool_results: List[Dict], 
                              schemas: Dict[str, Any], openai_client=None) -> ContextualResponse:
        """Generate a comprehensive contextual response."""
        
        # Build semantic context
        context = self.context_builder.build_context(tool_results, schemas, user_query)
        
        # Determine response type
        response_type = self._determine_response_type(context, user_query)
        
        # Generate insights
        insights = self._generate_insights(context, tool_results)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(context, insights)
        
        # Generate direct answer
        direct_answer = await self._generate_direct_answer(
            user_query, context, tool_results, openai_client
        )
        
        # Generate business context
        business_context = self._generate_business_context(context)
        
        # Generate follow-up questions
        follow_ups = self._generate_follow_up_questions(context, user_query)
        
        # Generate warnings
        warnings = self._generate_warnings(context)
        
        # Build data sources info
        data_sources = self._build_data_sources_info(tool_results)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(context, tool_results)
        
        return ContextualResponse(
            direct_answer=direct_answer,
            insights=insights,
            recommendations=recommendations,
            business_context=business_context,
            follow_up_questions=follow_ups,
            warnings=warnings,
            data_sources=data_sources,
            confidence_score=confidence_score
        )
    
    def _determine_response_type(self, context: Dict[str, Any], user_query: str) -> str:
        """Determine the type of response to generate."""
        intent = context.get('user_intent', {})
        primary_action = intent.get('primary_action', 'unknown')
        
        if primary_action == 'retrieve':
            if any(entity in intent.get('entities_mentioned', []) for entity in ['payment', 'account', 'balance']):
                return 'financial_summary'
            else:
                return 'status_update'
        elif primary_action == 'analyze':
            return 'analysis_report'
        elif primary_action == 'execute':
            return 'action_required'
        else:
            return 'financial_summary'
    
    def _generate_insights(self, context: Dict[str, Any], tool_results: List[Dict]) -> List[DataInsight]:
        """Generate data insights from the context."""
        insights = []
        
        # Risk-based insights
        risks = context.get('risk_indicators', [])
        for risk in risks:
            if risk['severity'] in ['high', 'medium']:
                insights.append(DataInsight(
                    type='risk',
                    message=f"Risk detected: {risk['value']} in {risk['path']}",
                    confidence=0.9 if risk['severity'] == 'high' else 0.7,
                    source_tools=[risk['source_tool']],
                    business_impact="May require immediate attention",
                    urgency=risk['severity']
                ))
        
        # Temporal insights
        temporal = context.get('temporal_patterns', {})
        overdue_items = temporal.get('overdue_items', [])
        if overdue_items:
            insights.append(DataInsight(
                type='temporal',
                message=f"You have {len(overdue_items)} overdue items requiring attention",
                confidence=0.95,
                source_tools=list(set(item['data'].get('tool', 'unknown') for item in overdue_items)),
                business_impact="Late fees or penalties may apply",
                urgency='high'
            ))
        
        upcoming_deadlines = temporal.get('upcoming_deadlines', [])
        urgent_deadlines = [d for d in upcoming_deadlines if d['days_until'] <= 3]
        if urgent_deadlines:
            insights.append(DataInsight(
                type='temporal',
                message=f"{len(urgent_deadlines)} deadlines approaching within 3 days",
                confidence=0.9,
                source_tools=list(set(item['data'].get('tool', 'unknown') for item in urgent_deadlines)),
                business_impact="Action required to meet deadlines",
                urgency='medium'
            ))
        
        # Financial insights
        metrics = context.get('business_metrics', {})
        total_amounts = metrics.get('total_amounts', {})
        if total_amounts:
            for currency, amount in total_amounts.items():
                if amount > 10000:  # Significant amount threshold
                    insights.append(DataInsight(
                        type='financial',
                        message=f"Significant amount involved: {amount:,.2f} {currency}",
                        confidence=0.8,
                        source_tools=[],
                        business_impact="Large financial exposure",
                        urgency='normal'
                    ))
        
        return insights
    
    def _generate_recommendations(self, context: Dict[str, Any], insights: List[DataInsight]) -> List[Recommendation]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Risk-based recommendations
        high_risk_insights = [i for i in insights if i.urgency == 'high']
        for insight in high_risk_insights:
            if insight.type == 'risk':
                recommendations.append(Recommendation(
                    action="Review and resolve the identified risk immediately",
                    reason=insight.message,
                    priority='critical',
                    timeline='immediate',
                    impact="Prevent potential financial loss or penalties",
                    tools_required=insight.source_tools
                ))
            elif insight.type == 'temporal':
                recommendations.append(Recommendation(
                    action="Address overdue items to avoid additional penalties",
                    reason="Items are past their due dates",
                    priority='high',
                    timeline='immediate',
                    impact="Minimize late fees and maintain good standing",
                    tools_required=insight.source_tools
                ))
        
        # Temporal recommendations
        temporal = context.get('temporal_patterns', {})
        upcoming_deadlines = temporal.get('upcoming_deadlines', [])
        if upcoming_deadlines:
            urgent = [d for d in upcoming_deadlines if d['days_until'] <= 7]
            if urgent:
                recommendations.append(Recommendation(
                    action="Schedule upcoming payments and tasks",
                    reason=f"{len(urgent)} items due within the next week",
                    priority='medium',
                    timeline='short-term',
                    impact="Ensure timely completion and avoid penalties"
                ))
        
        # Process optimization recommendations
        success_rate = context.get('business_metrics', {}).get('success_rate', 1.0)
        if success_rate < 0.9:
            recommendations.append(Recommendation(
                action="Review and optimize API call reliability",
                reason=f"Success rate is {success_rate:.1%}, below optimal threshold",
                priority='medium',
                timeline='long-term',
                impact="Improve data reliability and system performance"
            ))
        
        return recommendations
    
    async def _generate_direct_answer(self, user_query: str, context: Dict[str, Any], 
                                    tool_results: List[Dict], openai_client) -> str:
        """Generate a direct answer to the user's question."""
        
        # If we have OpenAI client, use it for intelligent response
        if openai_client:
            try:
                # Prepare context summary for the LLM
                context_summary = {
                    'entities': {k: len(v) for k, v in context.get('entities', {}).items()},
                    'risks': len(context.get('risk_indicators', [])),
                    'success_rate': context.get('business_metrics', {}).get('success_rate', 1.0),
                    'overdue_items': len(context.get('temporal_patterns', {}).get('overdue_items', [])),
                    'upcoming_deadlines': len(context.get('temporal_patterns', {}).get('upcoming_deadlines', []))
                }
                
                messages = [
                    {
                        "role": "system",
                        "content": """You are an expert financial assistant. Provide a clear, direct answer to the user's question based on the tool results and context. 
                        
Be concise but informative. Focus on the most important information first. Use natural language and avoid technical jargon."""
                    },
                    {
                        "role": "user",
                        "content": f"""User Question: {user_query}

Context Summary: {json.dumps(context_summary, indent=2)}

Tool Results: {json.dumps([r for r in tool_results if r.get('success')], indent=2)[:3000]}

Provide a direct, helpful answer to the user's question based on this information."""
                    }
                ]
                
                response = await openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    max_tokens=300,
                    temperature=0.3
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.error(f"Error generating AI response: {e}")
                # Fall back to template-based response
        
        # Template-based fallback response
        entities = context.get('entities', {})
        metrics = context.get('business_metrics', {})
        
        # Count successful results
        successful_tools = sum(1 for r in tool_results if r.get('success'))
        
        if successful_tools == 0:
            return "I wasn't able to retrieve the requested information. Please check your connection and try again."
        
        # Build a structured response
        parts = []
        
        # Summary of data retrieved
        data_summary = []
        for entity_type, entity_list in entities.items():
            if entity_list:
                data_summary.append(f"{len(entity_list)} {entity_type.replace('_', ' ')}")
        
        if data_summary:
            parts.append(f"I found {', '.join(data_summary)}.")
        
        # Key metrics
        total_amounts = metrics.get('total_amounts', {})
        if total_amounts:
            amount_strings = [f"{amount:,.2f} {currency}" for currency, amount in total_amounts.items()]
            parts.append(f"Total amounts: {', '.join(amount_strings)}.")
        
        # Risk indicators
        risks = context.get('risk_indicators', [])
        high_risks = [r for r in risks if r['severity'] == 'high']
        if high_risks:
            parts.append(f"⚠️ {len(high_risks)} high-priority items require attention.")
        
        return " ".join(parts) if parts else "Information retrieved successfully."
    
    def _generate_business_context(self, context: Dict[str, Any]) -> str:
        """Generate business context explanation."""
        context_parts = []
        
        # Data quality context
        quality = context.get('data_quality', {})
        completeness = quality.get('completeness', 0)
        if completeness < 1.0:
            context_parts.append(f"Data completeness: {completeness:.1%}")
        
        # Success rate context
        success_rate = context.get('business_metrics', {}).get('success_rate', 1.0)
        if success_rate < 1.0:
            context_parts.append(f"System reliability: {success_rate:.1%}")
        
        # Temporal context
        temporal = context.get('temporal_patterns', {})
        recent_activity = temporal.get('recent_activity', [])
        if recent_activity:
            context_parts.append(f"Recent activity detected in the last 7 days")
        
        if not context_parts:
            context_parts.append("All systems operating normally")
        
        return "Business context: " + "; ".join(context_parts) + "."
    
    def _generate_follow_up_questions(self, context: Dict[str, Any], user_query: str) -> List[str]:
        """Generate relevant follow-up questions."""
        follow_ups = []
        
        # Based on detected entities
        entities = context.get('entities', {})
        
        if entities.get('payments'):
            follow_ups.append("Would you like me to help you schedule or modify any payments?")
        
        if entities.get('financial_accounts'):
            follow_ups.append("Should I show you a detailed breakdown of account activity?")
        
        # Based on risks
        risks = context.get('risk_indicators', [])
        if risks:
            follow_ups.append("Would you like me to help resolve the identified issues?")
        
        # Based on temporal patterns
        temporal = context.get('temporal_patterns', {})
        upcoming_deadlines = temporal.get('upcoming_deadlines', [])
        if upcoming_deadlines:
            follow_ups.append("Shall I set up reminders for upcoming deadlines?")
        
        # Based on user intent
        intent = context.get('user_intent', {})
        if intent.get('primary_action') == 'retrieve':
            follow_ups.append("Would you like to see more detailed information or perform any actions?")
        
        # Generic helpful questions
        if not follow_ups:
            follow_ups.extend([
                "Is there anything specific you'd like me to help you with?",
                "Would you like me to monitor these items for changes?"
            ])
        
        return follow_ups[:3]  # Limit to 3 follow-up questions
    
    def _generate_warnings(self, context: Dict[str, Any]) -> List[str]:
        """Generate important warnings for the user."""
        warnings = []
        
        # Risk-based warnings
        risks = context.get('risk_indicators', [])
        critical_risks = [r for r in risks if r['severity'] == 'high']
        for risk in critical_risks:
            warnings.append(f"🚨 Critical: {risk['value']} detected in {risk['path']}")
        
        # Temporal warnings
        temporal = context.get('temporal_patterns', {})
        overdue_items = temporal.get('overdue_items', [])
        if overdue_items:
            total_overdue = len(overdue_items)
            max_days_overdue = max(item['days_overdue'] for item in overdue_items)
            warnings.append(f"⚠️ {total_overdue} overdue items (longest: {max_days_overdue} days)")
        
        # Data quality warnings
        quality = context.get('data_quality', {})
        completeness = quality.get('completeness', 1.0)
        if completeness < 0.8:
            warnings.append(f"📊 Data may be incomplete ({completeness:.1%} success rate)")
        
        return warnings
    
    def _build_data_sources_info(self, tool_results: List[Dict]) -> List[Dict[str, Any]]:
        """Build information about data sources."""
        sources = []
        
        for result in tool_results:
            tool_name = result.get('tool_name', 'unknown')
            success = result.get('success', False)
            
            source_info = {
                'tool': tool_name,
                'status': 'success' if success else 'failed',
                'confidence': 'high' if success else 'none',
                'timestamp': datetime.now().isoformat()
            }
            
            if not success:
                source_info['error'] = result.get('error', 'Unknown error')
            
            sources.append(source_info)
        
        return sources
    
    def _calculate_confidence_score(self, context: Dict[str, Any], tool_results: List[Dict]) -> float:
        """Calculate overall confidence score for the response."""
        factors = []
        
        # Success rate of tool calls
        total_tools = len(tool_results)
        successful_tools = sum(1 for r in tool_results if r.get('success'))
        success_rate = successful_tools / total_tools if total_tools > 0 else 0
        factors.append(success_rate)
        
        # Data completeness
        quality = context.get('data_quality', {})
        completeness = quality.get('completeness', 0)
        factors.append(completeness)
        
        # Data consistency
        consistency = quality.get('consistency', 0)
        factors.append(consistency)
        
        # Amount of data retrieved
        entities = context.get('entities', {})
        total_entities = sum(len(entity_list) for entity_list in entities.values())
        data_richness = min(1.0, total_entities / 10)  # Normalize to 0-1
        factors.append(data_richness)
        
        # Calculate weighted average
        weights = [0.4, 0.3, 0.2, 0.1]  # Prioritize success rate and completeness
        confidence = sum(f * w for f, w in zip(factors, weights)) / sum(weights)
        
        return round(confidence, 2)


# Usage example
async def main():
    """Test the context-aware response generator."""
    
    # Mock tool results
    mock_tool_results = [
        {
            'tool_name': 'cash_api_getPayments',
            'success': True,
            'result': {
                'payments': [
                    {
                        'id': 'PAY-001',
                        'amount': 1500.00,
                        'currency': 'USD',
                        'status': 'pending',
                        'dueDate': '2024-01-17T00:00:00Z',
                        'recipient': 'Landlord LLC',
                        'accountNumber': 'ACC-123'
                    },
                    {
                        'id': 'PAY-002',
                        'amount': 250.00,
                        'currency': 'USD',
                        'status': 'pending',
                        'dueDate': '2024-01-20T00:00:00Z',
                        'recipient': 'City Utilities',
                        'accountNumber': 'ACC-123'
                    }
                ]
            }
        },
        {
            'tool_name': 'cash_api_getAccounts',
            'success': True,
            'result': {
                'accounts': [
                    {
                        'accountNumber': 'ACC-123',
                        'balance': 15420.50,
                        'currency': 'USD',
                        'type': 'checking'
                    }
                ]
            }
        }
    ]
    
    # Mock schemas
    mock_schemas = {
        'cash_api_getPayments': {
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'enum': ['pending', 'completed', 'failed']},
                'amount': {'type': 'number', 'minimum': 0},
                'currency': {'type': 'string', 'format': 'currency-code'}
            }
        }
    }
    
    generator = ContextAwareResponseGenerator()
    
    print("🤖 Testing Context-Aware Response Generator")
    print("=" * 60)
    
    response = await generator.generate_response(
        user_query="Show me my pending payments",
        tool_results=mock_tool_results,
        schemas=mock_schemas
    )
    
    print(f"📝 Direct Answer:")
    print(response.direct_answer)
    print()
    
    print(f"💡 Insights ({len(response.insights)}):")
    for insight in response.insights:
        print(f"  • {insight.message} (confidence: {insight.confidence:.1%})")
    print()
    
    print(f"🎯 Recommendations ({len(response.recommendations)}):")
    for rec in response.recommendations:
        print(f"  • {rec.action} ({rec.priority} priority)")
        print(f"    Reason: {rec.reason}")
    print()
    
    print(f"🏢 Business Context:")
    print(f"  {response.business_context}")
    print()
    
    print(f"❓ Follow-up Questions:")
    for question in response.follow_up_questions:
        print(f"  • {question}")
    print()
    
    if response.warnings:
        print(f"⚠️ Warnings:")
        for warning in response.warnings:
            print(f"  • {warning}")
        print()
    
    print(f"📊 Confidence Score: {response.confidence_score:.1%}")
    print()
    print("🎯 Context-Aware Response Generator POC Complete!")

if __name__ == "__main__":
    asyncio.run(main())
