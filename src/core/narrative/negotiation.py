#!/usr/bin/env python3
"""
Multi-agent negotiation engine.

多Agent协商引擎 - 冲突解决与合作机制
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.llm_service import LLMRequest, ResponseFormat, get_llm_service

from .types import (
    NegotiationProposal,
    NegotiationResponse,
    NegotiationSession,
    NegotiationStatus,
)

logger = logging.getLogger(__name__)

class AgentNegotiationEngine:
    """多Agent协商引擎"""

    def __init__(self, llm_service=None):
        self.llm_service = llm_service or get_llm_service()
        self.active_sessions: Dict[str, NegotiationSession] = {}
        self.negotiation_history: List[NegotiationSession] = []
        self.agent_negotiation_profiles: Dict[str, Dict[str, Any]] = {}

    def initialize_agent_profile(
        self,
        agent_id: str,
        negotiation_style: Dict[str, float] = None,
        priorities: List[str] = None,
    ):
        """初始化Agent协商档案"""
        if negotiation_style is None:
            negotiation_style = {
                "cooperativeness": 0.5,
                "competitiveness": 0.5,
                "compromise_willingness": 0.6,
                "patience": 0.7,
                "trust_level": 0.5,
            }

        self.agent_negotiation_profiles[agent_id] = {
            "style": negotiation_style,
            "priorities": priorities or ["survival", "mission_success"],
            "successful_negotiations": 0,
            "failed_negotiations": 0,
            "reputation": 0.5,
        }

    async def initiate_negotiation(
        self,
        initiator_id: str,
        target_agents: List[str],
        topic: str,
        initial_proposal: Dict[str, Any],
    ) -> str:
        """发起协商"""
        session_id = str(uuid.uuid4())

        # 创建协商会话
        session = NegotiationSession(
            session_id=session_id,
            participants=[initiator_id] + target_agents,
            topic=topic,
            status=NegotiationStatus.INITIATED,
        )

        # 创建初始提议
        proposal = NegotiationProposal(
            proposal_id=str(uuid.uuid4()),
            proposer_id=initiator_id,
            proposal_type=initial_proposal.get("type", "general"),
            content=initial_proposal,
            target_agents=target_agents,
            expires_at=datetime.now() + timedelta(minutes=session.timeout_minutes),
        )

        session.proposals.append(proposal)
        self.active_sessions[session_id] = session

        logger.info(f"Negotiation initiated: {session_id} by {initiator_id}")

        # 通知目标Agent
        await self._notify_agents_of_proposal(proposal, target_agents)

        return session_id

    async def _notify_agents_of_proposal(
        self, proposal: NegotiationProposal, target_agents: List[str]
    ):
        """通知Agent收到新的协商提议"""
        # 这里应该集成到消息系统中
        for agent_id in target_agents:
            logger.debug(f"Notified {agent_id} of proposal {proposal.proposal_id}")

    async def respond_to_proposal(
        self,
        proposal_id: str,
        responder_id: str,
        response_type: str,
        response_content: Dict[str, Any] = None,
    ) -> bool:
        """回应协商提议"""

        # 查找包含此提议的会话
        session = None
        for s in self.active_sessions.values():
            if any(p.proposal_id == proposal_id for p in s.proposals):
                session = s
                break

        if not session:
            logger.warning(f"No active session found for proposal {proposal_id}")
            return False

        # 验证回应者是否为参与者
        if responder_id not in session.participants:
            logger.warning(
                f"Agent {responder_id} not participant in session {session.session_id}"
            )
            return False

        # 创建回应
        response = NegotiationResponse(
            response_id=str(uuid.uuid4()),
            proposal_id=proposal_id,
            responder_id=responder_id,
            response_type=response_type,
            content=response_content or {},
        )

        session.responses.append(response)
        session.updated_at = datetime.now()
        session.status = NegotiationStatus.IN_PROGRESS

        # 检查是否需要生成智能回应
        if response_type in ["counter", "conditional"]:
            await self._generate_intelligent_counter_proposal(session, response)

        # 检查协商状态
        await self._evaluate_negotiation_status(session)

        logger.debug(
            f"Response added to negotiation {session.session_id}: {response_type}"
        )
        return True

    async def _generate_intelligent_counter_proposal(
        self, session: NegotiationSession, response: NegotiationResponse
    ):
        """生成智能反提议"""
        if not self.llm_service:
            return

        # 获取协商历史和Agent档案
        responder_profile = self.agent_negotiation_profiles.get(
            response.responder_id, {}
        )

        # 构建LLM请求
        prompt = f"""
        基于以下协商情境，为Agent {response.responder_id}生成一个合理的反提议：

        协商主题：{session.topic}
        原始提议：{session.proposals[-1].content}
        Agent性格特征：{responder_profile.get('style', {})}
        Agent优先级：{responder_profile.get('priorities', [])}
        
        请生成一个JSON格式的反提议，包含：
        - type: 提议类型
        - content: 具体内容
        - requirements: 要求条件
        - benefits_offered: 提供的好处
        """

        try:
            llm_request = LLMRequest(
                prompt=prompt, response_format=ResponseFormat.JSON, max_tokens=500
            )

            llm_response = await self.llm_service.process_request(llm_request)

            if llm_response and llm_response.success:
                counter_proposal = json.loads(llm_response.content)
                response.counter_proposal = counter_proposal
                logger.debug(
                    f"Generated intelligent counter-proposal for {response.responder_id}"
                )

        except Exception as e:
            logger.error(f"Failed to generate counter-proposal: {e}")

    async def _evaluate_negotiation_status(self, session: NegotiationSession):
        """评估协商状态"""
        # 检查超时
        if datetime.now() > session.created_at + timedelta(
            minutes=session.timeout_minutes
        ):
            session.status = NegotiationStatus.TIMEOUT
            self._finalize_session(session)
            return

        # 检查是否所有参与者都已回应
        latest_proposal = session.proposals[-1] if session.proposals else None
        if not latest_proposal:
            return

        target_responses = [
            r for r in session.responses if r.proposal_id == latest_proposal.proposal_id
        ]

        if len(target_responses) >= len(latest_proposal.target_agents):
            # 所有目标Agent都已回应
            await self._attempt_resolution(session)

    async def _attempt_resolution(self, session: NegotiationSession):
        """尝试解决协商"""
        latest_proposal = session.proposals[-1]
        responses = [
            r for r in session.responses if r.proposal_id == latest_proposal.proposal_id
        ]

        # 统计回应类型
        accepts = [r for r in responses if r.response_type == "accept"]
        rejects = [r for r in responses if r.response_type == "reject"]
        counters = [
            r for r in responses if r.response_type in ["counter", "conditional"]
        ]

        # 决议逻辑
        if len(accepts) == len(responses):
            # 全部接受
            session.status = NegotiationStatus.RESOLVED
            session.resolution = {
                "type": "unanimous_acceptance",
                "proposal": latest_proposal.content,
                "participants": session.participants,
            }
            self._update_agent_reputations(session, success=True)

        elif len(rejects) > len(accepts):
            # 拒绝过多
            if len(counters) > 0:
                # 有反提议，继续协商
                await self._handle_counter_proposals(session, counters)
            else:
                # 无反提议，协商失败
                session.status = NegotiationStatus.FAILED
                self._update_agent_reputations(session, success=False)

        else:
            # 混合回应，尝试智能调解
            await self._intelligent_mediation(session, responses)

        if session.status in [
            NegotiationStatus.RESOLVED,
            NegotiationStatus.FAILED,
            NegotiationStatus.TIMEOUT,
        ]:
            self._finalize_session(session)

    async def _handle_counter_proposals(
        self, session: NegotiationSession, counters: List[NegotiationResponse]
    ):
        """处理反提议"""
        if not counters:
            return

        # 选择最有希望的反提议
        best_counter = max(
            counters,
            key=lambda x: self._evaluate_proposal_viability(x.counter_proposal),
        )

        # 创建新的提议基于最佳反提议
        new_proposal = NegotiationProposal(
            proposal_id=str(uuid.uuid4()),
            proposer_id=best_counter.responder_id,
            proposal_type=best_counter.counter_proposal.get("type", "counter"),
            content=best_counter.counter_proposal,
            target_agents=[
                aid for aid in session.participants if aid != best_counter.responder_id
            ],
            expires_at=datetime.now() + timedelta(minutes=session.timeout_minutes // 2),
        )

        session.proposals.append(new_proposal)
        await self._notify_agents_of_proposal(new_proposal, new_proposal.target_agents)

        logger.info(f"New counter-proposal created in session {session.session_id}")

    def _evaluate_proposal_viability(self, proposal: Dict[str, Any]) -> float:
        """评估提议的可行性"""
        if not proposal:
            return 0.0

        # 简化的可行性评分
        score = 0.5  # 基础分

        # 根据提议内容调整分数
        if "benefits_offered" in proposal and proposal["benefits_offered"]:
            score += 0.2

        if "requirements" in proposal:
            req_count = len(proposal["requirements"])
            score -= min(0.3, req_count * 0.1)  # 要求越多，分数越低

        return max(0.0, min(1.0, score))

    async def _intelligent_mediation(
        self, session: NegotiationSession, responses: List[NegotiationResponse]
    ):
        """智能调解"""
        if not self.llm_service:
            session.status = NegotiationStatus.DEADLOCK
            return

        # 构建调解请求
        mediation_context = {
            "topic": session.topic,
            "original_proposal": session.proposals[-1].content,
            "responses": [
                {"agent": r.responder_id, "type": r.response_type, "content": r.content}
                for r in responses
            ],
            "participant_profiles": {
                aid: self.agent_negotiation_profiles.get(aid, {})
                for aid in session.participants
            },
        }

        prompt = f"""
        作为智能调解员，请为以下协商冲突提供解决方案：

        协商情况：{json.dumps(mediation_context, indent=2)}

        请生成一个妥协方案，包含：
        - 调解后的提议内容
        - 对每个参与者的好处说明
        - 实施建议

        返回JSON格式结果。
        """

        try:
            llm_request = LLMRequest(
                prompt=prompt, response_format=ResponseFormat.JSON, max_tokens=800
            )

            llm_response = await self.llm_service.process_request(llm_request)

            if llm_response and llm_response.success:
                mediation_result = json.loads(llm_response.content)

                # 创建调解提议
                mediated_proposal = NegotiationProposal(
                    proposal_id=str(uuid.uuid4()),
                    proposer_id="mediator",
                    proposal_type="mediated_compromise",
                    content=mediation_result,
                    target_agents=session.participants,
                    expires_at=datetime.now() + timedelta(minutes=15),
                )

                session.proposals.append(mediated_proposal)
                await self._notify_agents_of_proposal(
                    mediated_proposal, session.participants
                )

                logger.info(
                    f"Mediated proposal created for session {session.session_id}"
                )
            else:
                session.status = NegotiationStatus.DEADLOCK

        except Exception as e:
            logger.error(f"Mediation failed: {e}")
            session.status = NegotiationStatus.DEADLOCK

    def _update_agent_reputations(self, session: NegotiationSession, success: bool):
        """更新Agent声誉"""
        for agent_id in session.participants:
            if agent_id in self.agent_negotiation_profiles:
                profile = self.agent_negotiation_profiles[agent_id]
                if success:
                    profile["successful_negotiations"] += 1
                    profile["reputation"] = min(1.0, profile["reputation"] + 0.1)
                else:
                    profile["failed_negotiations"] += 1
                    profile["reputation"] = max(0.0, profile["reputation"] - 0.05)

    def _finalize_session(self, session: NegotiationSession):
        """结束协商会话"""
        if session.session_id in self.active_sessions:
            del self.active_sessions[session.session_id]

        self.negotiation_history.append(session)
        logger.info(
            f"Negotiation session {session.session_id} finalized with status: {session.status}"
        )

    def get_negotiation_summary(self, session_id: str) -> Dict[str, Any]:
        """获取协商摘要"""
        # 在活跃会话中查找
        session = self.active_sessions.get(session_id)

        # 在历史记录中查找
        if not session:
            for hist_session in self.negotiation_history:
                if hist_session.session_id == session_id:
                    session = hist_session
                    break

        if not session:
            return {}

        return {
            "session_id": session.session_id,
            "participants": session.participants,
            "topic": session.topic,
            "status": session.status.value,
            "proposal_count": len(session.proposals),
            "response_count": len(session.responses),
            "duration_minutes": (
                session.updated_at - session.created_at
            ).total_seconds()
            / 60,
            "resolution": session.resolution,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

