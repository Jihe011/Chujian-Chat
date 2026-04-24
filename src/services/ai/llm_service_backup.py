
    # Simplified file with correct indentation
    import datetime as dt
    
    class LLMService:
        def __init__(self, api_key, model, temperature=0.75, max_tokens=2048, allow_custom=True): 
            self.api_key = api_key
            self.model = model
            self.temperature = temperature
            self.max_tokens = max_tokens
            self.allow_custom = allow_custom
            self.chat_contexts = {}
            self.enable_time_context = True
            
        def _get_time_period(self):
            hour = dt.now().hour
            if hour < 5: return 'ÉîÒ¹'
            elif hour < 7: return 'Áè³¿'
            elif hour < 9: return 'Ôç³¿'
            elif hour < 12: return 'ÉÏÎç'
            elif hour < 14: return 'ÖÐÎç'
            elif hour < 17: return 'ÏÂÎç'
            elif hour < 19: return '°øÍí'
            else: return 'ÍíÉÏ'
            
        def _get_period_activity_suggestion(self, period):
            suggestions = {
                'Áè³¿': '°²¾²ÐÝÏ¢',
                'Ôç³¿': 'Ôç°²ÎÊºò',
                'ÉÏÎç': '¹¤×÷Ñ§Ï°',
                'ÖÐÎç': 'Îç²ÍÎçÐÝ',
                'ÏÂÎç': 'ÏÂÎç²è½»Á÷',
                '°øÍí': 'Íí²ÍÐÝÏ¢',
                'ÍíÉÏ': 'ÓéÀÖÁÄÌì',
                'ÉîÒ¹': '±ÜÃâ´òÈÅ'
            }
            return suggestions.get(period, '')
            
        def get_response(self, message, user_id, system_prompt, previous_context=None, core_memory=None, enable_search=None):
            time_period = self._get_time_period()
            suggestion = self._get_period_activity_suggestion(time_period)
            
            now = dt.now()
            time_prompt = f"µ±Ç°Ê±¼ä: {now.strftime('%Y-%m-%d %H:%M:%S')}, {time_period}"
            
            # Combine prompts
            full_prompt = f"{time_prompt}. {suggestion}"
            
            if previous_context:
                context = '
'.join([f"{m["role"]}: {m["content"]}" for m in previous_context])
                full_prompt += f"

Context: {context}"
            
            full_prompt += f"

{system_prompt}"
            
            # Simulate response
            return f"Time-aware response to: {message}"
            
        def clear_history(self, user_id):
            if user_id in self.chat_contexts:
                del self.chat_contexts[user_id]
                return True
            return False
