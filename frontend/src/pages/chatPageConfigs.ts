import type { ChatFeature } from '../hooks/chatConfigs'
import type { HeaderProps } from '../components/Header/Header'
import type { AppErrorType } from '../types/error'

type SubmitPlanConfig = {
  submitEndpoint: string
  fetchSummaryAfterSubmit?: boolean
  navigateToCompleteOnSuccess?: boolean
  toastOnError?: string
  toastErrorTypes?: AppErrorType[]
  addSystemMessageOnSubmit?: boolean
}

export type ChatPageConfig = {
  feature: ChatFeature
  themeClassName: string
  header: HeaderProps
  samplePrompts: string[]
  planSyncMode: 'defined' | 'truthy'
  submitPlan?: SubmitPlanConfig
}

export const CHAT_PAGE_CONFIGS: Record<ChatFeature, ChatPageConfig> = {
  travel: {
    feature: 'travel',
    themeClassName: 'theme-travel',
    header: {},
    planSyncMode: 'truthy',
    samplePrompts: [
      'どこに行くのがおすすめ？',
      'どんな有名スポットがある？',
      '落ち着ける場所はある？',
      'ご飯に行くならどこ？',
    ],
    submitPlan: {
      submitEndpoint: '/travel_submit_plan',
      fetchSummaryAfterSubmit: true,
      addSystemMessageOnSubmit: true,
    },
  },
  reply: {
    feature: 'reply',
    themeClassName: 'theme-reply',
    header: { subtitle: '返信作成アシスタント' },
    planSyncMode: 'defined',
    samplePrompts: [
      '相手:「火曜14時どうですか？」\n意図: 木曜16時を提案\n条件: 丁寧、80文字以内',
      '相手:「今月の飲み会来られる？」\n意図: 今回は不参加、次回は参加したい\n条件: カジュアルで角が立たない',
      '相手:「資料まだですか？」\n意図: 遅れを謝り、20時までに送る\n条件: 誠実で簡潔',
      '相手:「先日はありがとうございました！」\n意図: お礼を返して来週の日程相談\n条件: 丁寧で前向き、120文字以内',
    ],
    submitPlan: {
      submitEndpoint: '/reply_submit_plan',
      navigateToCompleteOnSuccess: true,
      toastOnError: 'プランの保存に失敗しました。',
    },
  },
  fitness: {
    feature: 'fitness',
    themeClassName: 'theme-fitness',
    header: { subtitle: '筋トレ・フィットネスアシスタント' },
    planSyncMode: 'defined',
    samplePrompts: [
      '筋肥大したい。週3回でどんなメニューが良い？',
      '運動初心者。まず何から始めればいい？',
      '肩こり改善のための簡単な運動は？',
      '自宅でできる減量メニューを教えて',
    ],
  },
  job: {
    feature: 'job',
    themeClassName: 'theme-job',
    header: { subtitle: '就活アシスタント' },
    planSyncMode: 'defined',
    samplePrompts: [
      '自己PRを400字で作りたい。強みは継続力。',
      'ESのガクチカを添削してほしい。',
      '志望動機を業界研究ベースで作ってほしい。',
      '面接の想定質問と回答の骨子を作って。',
    ],
  },
  study: {
    feature: 'study',
    themeClassName: 'theme-study',
    header: { subtitle: '学習アシスタント' },
    planSyncMode: 'defined',
    samplePrompts: [
      '今日の授業メモを整理ノートにして。',
      '用語集を作って。',
      '重要ポイントを短くまとめて。',
      '確認問題を作って。',
    ],
  },
}
