<template>
  <main class="fitness-shell">
    <header class="fitness-topbar">
      <a class="brand" href="/niu-secretary/" aria-label="牛秘书塑形馆首页">
        <span class="brand-mark">牛</span>
        <span class="brand-text">
          <strong>牛秘书塑形馆</strong>
          <small>少点玄学，多点肌肉证据</small>
        </span>
      </a>
      <nav class="module-nav" aria-label="塑形馆模块">
        <button
          v-for="section in navSections"
          :key="section.key"
          type="button"
          class="nav-chip"
          :class="{ active: activeSection === section.key }"
          @click="activeSection = section.key"
        >{{ section.label }}</button>
      </nav>
      <div class="topbar-actions">
        <router-link class="home-link" to="/">返回主页</router-link>
        <div class="status-pill" :class="loading ? 'offline' : 'online'">{{ loading ? '同步中' : '在线' }}</div>
      </div>
    </header>

    <div class="fitness-content">
      <section class="hero-panel">
        <div class="hero-panel-inner">
          <div class="hero-intro">
            <p class="eyebrow">Health Workbench</p>
            <h1>身体账本</h1>
            <p class="hero-sub">练了多少，吃了多少，还差多少。</p>
          </div>
          <div class="hero-metrics" aria-label="今日概览">
            <div v-for="metric in heroMetrics" :key="metric.label" class="hero-metric">
              <div class="hero-metric-inner">
                <span>{{ metric.value }}</span>
                <small>{{ metric.label }}</small>
              </div>
            </div>
          </div>
        </div>
      </section>

      <el-alert v-if="loadError" class="fitness-alert" type="error" :title="loadError" show-icon :closable="false" />
      <div
        v-if="operationFeedback"
        :class="['fitness-operation-feedback', operationFeedback.type]"
        :role="operationFeedback.type === 'error' ? 'alert' : 'status'"
        aria-live="polite"
      >
        <span aria-hidden="true"></span>
        <div><strong>{{ operationFeedback.title }}</strong><small>{{ operationFeedback.detail }}</small></div>
      </div>

      <div class="section-host">
        <section v-show="activeSection === 'dashboard'" class="dashboard-grid workbench-section">
          <article class="glass-card full-row priority-card">
            <div class="glass-card-inner">
              <div class="card-head">
                <div>
                  <h2>我的画像 · 个性化推荐</h2>
                  <p>由牛秘书 AI 根据你的对话与记录生成，这里只读展示。</p>
                </div>
              </div>
              <div class="profile-panel">
                <div class="profile-section">
                  <h3>健身画像</h3>
                  <div class="profile-fields">
                    <div v-for="row in profileRows" :key="row.label" class="profile-row">
                      <span class="profile-label">{{ row.label }}</span>
                      <span class="profile-value">{{ row.value }}</span>
                    </div>
                  </div>
                </div>
                <div class="profile-section">
                  <h3>今日推荐</h3>
                  <ul class="recommend-list">
                    <li v-for="(rec, i) in workoutRecommendation" :key="i">{{ rec }}</li>
                    <li v-if="!workoutRecommendation.length" class="recommend-placeholder">暂无推荐，保存训练与恢复记录后生成。</li>
                  </ul>
                </div>
              </div>
            </div>
          </article>

          <div class="dashboard-pair dashboard-pair-trends full-row">
            <article class="glass-card priority-card paired-card">
              <div class="glass-card-inner">
                <div class="card-head">
                  <div>
                    <h2>趋势总览</h2>
                    <p>体重以 7 日均线判断方向，避免被单日水分波动误导。</p>
                  </div>
                </div>
                <div class="metric-row">
                  <div class="metric good"><b>{{ latestMetric?.weightKg ? latestMetric.weightKg.toFixed(1) : '--' }}</b><span>最新体重 kg</span></div>
                  <div class="metric warn"><b>{{ weightDelta }}</b><span>7 日变化 kg</span></div>
                  <div class="metric info"><b>{{ bmiText }}</b><span>BMI</span></div>
                </div>
                <div class="chart-wrap" aria-label="体重趋势图">
                  <div ref="weightChartEl" class="fitness-chart-inner"></div>
                  <span v-if="!hasWeightTrend" class="chart-empty">录入体重后生成趋势图</span>
                </div>
              </div>
            </article>

            <article class="glass-card paired-card">
              <div class="glass-card-inner">
                <div class="card-head">
                  <div>
                    <h3>录入体重</h3>
                    <p>写入走统一动作接口，本地仅保留离线缓存。</p>
                  </div>
                </div>
                <form class="fit-form" @submit.prevent="saveMetric">
                  <div class="form-grid">
                    <label class="field">日期<el-date-picker v-model="metricForm.date" type="date" value-format="YYYY-MM-DD" /></label>
                    <label class="field">体重 kg<el-input-number v-model="metricForm.weightKg" :min="20" :max="300" :precision="1" controls-position="right" /></label>
                    <label class="field">体脂 %<el-input-number v-model="metricForm.bodyFatPct" :min="3" :max="70" :precision="1" controls-position="right" /></label>
                    <label class="field">腰围 cm<el-input-number v-model="metricForm.waistCm" :min="40" :max="220" :precision="1" controls-position="right" /></label>
                    <label class="field field-wide">备注<el-input v-model="metricForm.note" maxlength="80" placeholder="训练日、外食、水肿等" /></label>
                  </div>
                  <div class="actions">
                    <el-button type="primary" :loading="saving === 'metric'" @click="saveMetric">保存记录</el-button>
                  </div>
                </form>
              </div>
            </article>
          </div>

          <div class="dashboard-pair dashboard-pair-nutrition full-row">
            <article class="glass-card paired-card">
              <div class="glass-card-inner">
                <div class="card-head">
                  <div>
                    <h3>今日营养</h3>
                    <p>读取今日真实饮食记录，拍照、估算和手动补录都会汇总到这里。</p>
                  </div>
                </div>
                <div class="rings">
                  <div class="ring" :style="ringStyle"><strong>{{ caloriePercent }}%</strong></div>
                  <div class="target-list">
                    <div v-for="macro in macroRows" :key="macro.label" class="target-row">
                      <span>{{ macro.label }}</span>
                      <div class="bar" :class="{ 'over-limit': macro.percent >= 100 }"><span :style="{ width: macro.percent + '%' }"></span></div>
                      <b>{{ macro.value }} / {{ macro.target }} {{ macro.unit }}</b>
                    </div>
                  </div>
                </div>
              </div>
            </article>

            <article class="glass-card paired-card">
              <div class="glass-card-inner">
                <div class="card-head">
                  <div>
                    <h3>目标设置</h3>
                    <p>读取统一 API；目标在个人画像中维护。</p>
                  </div>
                </div>
                <div class="goal-grid">
                  <div class="goal-cell"><b>{{ targets.calories }}</b><span>目标热量 kcal</span></div>
                  <div class="goal-cell"><b>{{ targets.proteinG }}</b><span>蛋白 g</span></div>
                  <div class="goal-cell"><b>{{ targets.carbsG }}</b><span>碳水 g</span></div>
                  <div class="goal-cell"><b>{{ targets.fatG }}</b><span>脂肪 g</span></div>
                  <div class="goal-cell"><b>{{ profile.heightCm || '--' }}</b><span>身高 cm</span></div>
                  <div class="goal-cell"><b>{{ profile.age || '--' }}</b><span>年龄</span></div>
                </div>
              </div>
            </article>
          </div>

          <article class="glass-card full-row history-card">
            <div class="glass-card-inner">
              <div class="card-head">
                <div>
                  <h3>最近记录</h3>
                  <p>在线读取统一 API；接口不可用时使用浏览器离线缓存。</p>
                </div>
              </div>
              <div class="log-list">
                <div v-for="row in recentRecords" :key="row.id" class="log-item">
                  <div class="log-item-main"><strong>{{ row.title }}</strong><small>{{ row.date }} · {{ row.type }}</small></div>
                  <span class="log-item-detail">{{ row.detail }}</span>
                </div>
                <p v-if="!recentRecords.length" class="empty">暂无记录，开始录入后这里会汇总。</p>
              </div>
            </div>
          </article>
        </section>

        <section v-show="activeSection === 'assessment'" class="assessment-layout workbench-section">
          <article class="glass-card priority-card assessment-main">
            <div class="glass-card-inner">
              <div class="card-head"><div><h2>身体评估</h2><p>按段录入，缺项可留空；保存后生成 BMI、TDEE 与训练限制。</p></div></div>
              <div class="assessment-progress" aria-live="polite">
                <div><span>第 {{ activeAssessmentIndex + 1 }} / {{ assessmentSections.length }} 段</span><strong>{{ activeAssessmentLabel }}</strong></div>
                <div class="assessment-progress-track"><i :style="{ width: assessmentProgress + '%' }"></i></div>
              </div>
              <div class="assessment-workflow">
                <nav class="assessment-section-nav">
                  <button
                    v-for="section in assessmentSections"
                    :key="section.key"
                    type="button"
                    :class="{ active: activeAssessmentSection === section.key }"
                    :data-assessment-section-target="section.key"
                    :aria-current="activeAssessmentSection === section.key ? 'step' : undefined"
                    @click="activeAssessmentSection = section.key"
                  >
                    <span>{{ section.index }}</span>
                    <strong>{{ section.label }}</strong>
                    <small>{{ section.hint }}</small>
                  </button>
                </nav>
                <div class="assessment-section-panel">
                  <section v-show="activeAssessmentSection === 'baseline'" class="assessment-section" data-assessment-section="baseline">
                    <div class="section-title compact"><h3>基础信息</h3><span>计算 BMI、BMR 和 TDEE</span></div>
                    <div class="form-grid">
                      <label class="field">日期<el-date-picker v-model="assessmentForm.date" type="date" value-format="YYYY-MM-DD" /></label>
                      <label class="field">目标<el-select v-model="assessmentForm.goal"><el-option label="身体重组" value="recomp" /><el-option label="减脂" value="fat_loss" /><el-option label="增肌" value="muscle_gain" /><el-option label="体态改善" value="posture" /></el-select></label>
                      <label class="field">身高 cm<el-input-number v-model="assessmentForm.heightCm" :min="120" :max="230" controls-position="right" /></label>
                      <label class="field">体重 kg<el-input-number v-model="assessmentForm.weightKg" :min="20" :max="300" :precision="1" controls-position="right" /></label>
                      <label class="field">年龄<el-input-number v-model="assessmentForm.age" :min="12" :max="90" controls-position="right" /></label>
                      <label class="field">性别<el-select v-model="assessmentForm.sex"><el-option label="男" value="male" /><el-option label="女" value="female" /></el-select></label>
                      <label class="field">活动系数<el-input-number v-model="assessmentForm.activity" :min="1.2" :max="2.2" :step="0.05" :precision="2" controls-position="right" /></label>
                    </div>
                  </section>
                  <section v-show="activeAssessmentSection === 'girths'" class="assessment-section" data-assessment-section="girths">
                    <div class="section-title compact"><h3>围度数据</h3><span>腰臀胸臂腿，缺项可留空</span></div>
                    <div class="form-grid">
                      <label class="field">腰围 cm<el-input-number v-model="assessmentForm.waistCm" :min="40" :max="220" :precision="1" controls-position="right" /></label>
                      <label class="field">体脂 %<el-input-number v-model="assessmentForm.bodyFatPct" :min="3" :max="70" :precision="1" controls-position="right" /></label>
                      <label v-for="f in assessmentGirthFields" :key="f.key" class="field">{{ f.label }}<el-input-number v-model="assessmentForm[f.key]" :min="15" :max="220" :precision="1" controls-position="right" /></label>
                    </div>
                  </section>
                  <section v-show="activeAssessmentSection === 'fms'" class="assessment-section" data-assessment-section="fms">
                    <div class="section-title compact"><h3>FMS 动作评分</h3><span>0-3 分，默认 2 分</span></div>
                    <div class="score-strip">
                      <label v-for="f in fmsFields" :key="f.key"><span>{{ f.label }}</span><el-input-number v-model="fmsScores[f.key]" :min="0" :max="3" controls-position="right" /></label>
                    </div>
                    <div class="assessment-preview">
                      <span><strong>{{ fmsTotal }}</strong>FMS 总分</span>
                      <span><strong>{{ fmsRiskLabel }}</strong>动作风险</span>
                    </div>
                  </section>
                  <section v-show="activeAssessmentSection === 'posture'" class="assessment-section" data-assessment-section="posture">
                    <div class="section-title compact"><h3>体态观察</h3><span>只勾选已经确认的问题</span></div>
                    <el-checkbox-group v-model="postureFlags" class="check-grid">
                      <el-checkbox-button v-for="flag in postureOptions" :key="flag" :label="flag" :value="flag" />
                    </el-checkbox-group>
                  </section>
                </div>
              </div>
              <div class="actions">
                <el-button type="primary" :loading="saving === 'assessment'" @click="saveAssessment">保存评估</el-button>
                <el-button @click="goNextAssessmentSection">{{ activeAssessmentIndex === assessmentSections.length - 1 ? '回到基础信息' : '下一段' }}</el-button>
              </div>
            </div>
          </article>

          <aside class="stack">
            <article class="glass-card result-panel status-card">
              <div class="glass-card-inner">
                <div class="card-head"><div><h3>评估结果</h3><p>实时预览，保存后写入历史。</p></div></div>
                <div class="result-grid">
                  <div><b>{{ assessmentPreview.bmi }}</b><span>BMI</span></div>
                  <div><b>{{ assessmentPreview.bmr }}</b><span>BMR kcal</span></div>
                  <div><b>{{ assessmentPreview.tdee }}</b><span>TDEE kcal</span></div>
                  <div><b>{{ fmsTotal }}</b><span>FMS 总分</span></div>
                </div>
              </div>
            </article>
          </aside>

          <article class="glass-card full-row history-card">
            <div class="glass-card-inner">
              <div class="card-head"><div><h3>评估历史</h3><p>在线读取统一 API；IndexedDB 只补充离线待同步记录。</p></div></div>
              <div class="log-list">
                <div v-for="row in assessmentHistory" :key="row.id" class="log-item">
                  <div class="log-item-main"><strong>{{ row.title }}</strong><small>{{ row.date }}</small></div>
                  <span class="log-item-detail">{{ row.detail }}</span>
                </div>
                <p v-if="!assessmentLogs.length" class="empty">暂无评估记录。</p>
              </div>
            </div>
          </article>
        </section>

        <section v-show="activeSection === 'training'" class="module-grid workbench-section">
          <article class="glass-card priority-card">
            <div class="glass-card-inner">
              <div class="card-head"><div><h2>训练记录</h2><p>记录名称、时长、强度与消耗，自动汇总本周训练量。</p></div></div>
              <form class="fit-form" @submit.prevent="saveWorkout">
                <div class="form-grid">
                  <label class="field">日期<el-date-picker v-model="workoutForm.date" type="date" value-format="YYYY-MM-DD" /></label>
                  <label class="field">训练名称<el-input v-model="workoutForm.name" placeholder="深蹲 / 上肢力量 / 有氧" /></label>
                  <label class="field">分钟<el-input-number v-model="workoutForm.durationMin" :min="0" controls-position="right" /></label>
                  <label class="field">强度<el-select v-model="workoutForm.intensity"><el-option label="低" value="low" /><el-option label="中" value="medium" /><el-option label="高" value="high" /></el-select></label>
                  <label class="field">消耗 kcal<el-input-number v-model="workoutForm.calories" :min="0" controls-position="right" /></label>
                  <label class="field field-wide">备注<el-input v-model="workoutForm.note" maxlength="80" placeholder="动作感觉、疼痛、替代动作等" /></label>
                </div>
                <div class="actions"><el-button type="primary" :loading="saving === 'workout'" @click="saveWorkout">保存训练</el-button></div>
              </form>
            </div>
          </article>
          <aside class="stack">
            <article class="glass-card status-card">
              <div class="glass-card-inner">
                <div class="card-head"><div><h3>本周训练</h3><p>聚合最近 7 天的训练记录。</p></div></div>
                <div class="metric-row">
                  <div class="metric good"><b>{{ weeklySummary.workoutCount || 0 }}</b><span>训练次数</span></div>
                  <div class="metric warn"><b>{{ weeklySummary.workoutMinutes || 0 }}</b><span>总分钟</span></div>
                  <div class="metric info"><b>{{ weeklySummary.workoutCalories || 0 }}</b><span>消耗 kcal</span></div>
                </div>
              </div>
            </article>
            <article class="glass-card">
              <div class="glass-card-inner">
                <div class="card-head"><div><h3>今日建议</h3><p>综合恢复状态与训练记录。</p></div></div>
                <ul class="recommend-list">
                  <li v-for="(rec, i) in workoutRecommendation" :key="i">{{ rec }}</li>
                  <li v-if="!workoutRecommendation.length" class="recommend-placeholder">暂无建议，保存训练与恢复记录后生成。</li>
                </ul>
              </div>
            </article>
          </aside>
          <article class="glass-card full-row history-card">
            <div class="glass-card-inner">
              <div class="card-head"><div><h3>最近训练</h3><p>在线读取统一 API；IndexedDB 只补充离线待同步记录。</p></div></div>
              <div class="log-list">
                <div v-for="row in workoutLogs" :key="row.id" class="log-item">
                  <div class="log-item-main"><strong>{{ row.name }}</strong><small>{{ row.date }} · {{ intensityLabel(row.intensity) }}</small></div>
                  <span class="log-item-detail">{{ row.durationMin }} 分钟 / {{ row.calories || 0 }} kcal</span>
                </div>
                <p v-if="!workoutLogs.length" class="empty">暂无训练记录。</p>
              </div>
            </div>
          </article>
        </section>

        <section v-show="activeSection === 'nutrition'" class="nutrition-layout workbench-section">
          <article class="glass-card photo-card priority-card nutrition-photo">
            <div class="glass-card-inner">
              <div class="card-head"><div><h2>拍照记一餐</h2><p>上传餐食图片后先识别、再确认。Agent 不可用时会明确降级为本地估算。</p></div></div>
              <el-upload drag :auto-upload="false" :limit="1" accept="image/*" :on-change="handlePhotoChange" :on-remove="clearPhoto" class="fit-upload">
                <span class="drop-icon">+</span>
                <strong>上传这一餐</strong>
                <small>支持手机拍照。尽量拍到整盘食物和份量参照。</small>
              </el-upload>
              <label class="field field-wide" style="margin-top:14px">补充描述<el-input v-model="photoForm.description" placeholder="例：红烧肉半份、米饭一碗、奶茶三分糖" /></label>
              <div v-if="recognitionState" class="recognition-state" :data-state="recognitionState.type === 'success' ? 'success' : recognitionState.type === 'error' ? 'failed' : recognitionState.type === 'warning' ? 'estimate' : 'loading'">{{ recognitionState.message }}</div>
              <div class="actions">
                <el-button type="primary" :loading="recognizing" @click="recognizePhoto">Agent 识别</el-button>
                <el-button @click="estimatePhoto">本地估算</el-button>
                <el-button :disabled="!recognizedMeal" @click="applyRecognizedToForm">转手动补录</el-button>
              </div>
              <div v-if="recognizedMeal" class="recognized-meal">
                <div class="card-head compact-head"><div><h3>待确认结果</h3><p>{{ recognizedMeal.source }} · 置信度 {{ Math.round(recognizedMeal.confidence * 100) }}%</p></div></div>
                <div class="mini-columns">
                  <div><strong>{{ recognizedMeal.food }}</strong><p>{{ recognizedMeal.calories }} kcal · 蛋白 {{ recognizedMeal.proteinG }}g · 碳水 {{ recognizedMeal.carbsG }}g · 脂肪 {{ recognizedMeal.fatG }}g</p></div>
                  <div v-if="recognizedMeal.warnings.length"><strong>提醒</strong><ul><li v-for="(w, i) in recognizedMeal.warnings" :key="i">{{ w }}</li></ul></div>
                </div>
                <div class="actions"><el-button type="primary" :loading="saving === 'nutrition'" @click="saveRecognizedNutrition">确认写入日志</el-button></div>
              </div>
            </div>
          </article>
          <article class="glass-card nutrition-manual">
            <div class="glass-card-inner">
              <div class="card-head"><div><h2>手动补录</h2><p>无法识别或份量不准时，手动数据优先。</p></div></div>
              <form class="fit-form" @submit.prevent="saveNutrition">
                <div class="form-grid">
                  <label class="field">日期<el-date-picker v-model="nutritionForm.date" type="date" value-format="YYYY-MM-DD" /></label>
                  <label class="field">食物描述<el-input v-model="nutritionForm.food" placeholder="红烧肉、米饭、奶茶" /></label>
                  <label class="field">热量 kcal<el-input-number v-model="nutritionForm.calories" :min="0" :max="5000" controls-position="right" /></label>
                  <label class="field">蛋白 g<el-input-number v-model="nutritionForm.proteinG" :min="0" :max="300" controls-position="right" /></label>
                  <label class="field">碳水 g<el-input-number v-model="nutritionForm.carbsG" :min="0" :max="600" controls-position="right" /></label>
                  <label class="field">脂肪 g<el-input-number v-model="nutritionForm.fatG" :min="0" :max="300" controls-position="right" /></label>
                </div>
                <div class="actions"><el-button type="primary" :loading="saving === 'nutrition'" @click="saveNutrition">保存饮食</el-button></div>
              </form>
            </div>
          </article>
          <article class="glass-card history-card nutrition-history">
            <div class="glass-card-inner">
              <div class="card-head"><div><h3>最近饮食</h3><p>在线读取统一 API；IndexedDB 只补充离线待同步记录。</p></div></div>
              <div class="log-list">
                <div v-for="row in nutritionLogs" :key="row.id" class="log-item">
                  <div class="log-item-main"><strong>{{ row.food }}</strong><small>{{ row.date }}</small></div>
                  <span class="log-item-detail">{{ row.calories }} kcal / 蛋白 {{ row.proteinG }}g</span>
                </div>
                <p v-if="!nutritionLogs.length" class="empty">暂无饮食记录。</p>
              </div>
            </div>
          </article>
          <aside class="stack nutrition-side">
            <article class="glass-card deficit-card status-card">
              <div class="glass-card-inner">
                <div class="card-head"><div><h3>今日热量缺口</h3><p>日常代谢 - 今日摄入。</p></div></div>
                <div class="deficit-number" :class="{ 'over-limit': deficitValue < 0 }">{{ deficitValue > 0 ? '+' : '' }}{{ deficitValue }}</div>
                <div class="deficit-subtitle">{{ deficitValue >= 0 ? '热量缺口，方向正确' : '热量盈余，注意摄入' }}</div>
              </div>
            </article>
          </aside>
        </section>

        <section v-show="activeSection === 'recovery'" class="module-grid workbench-section">
          <article class="glass-card priority-card">
            <div class="glass-card-inner">
              <div class="card-head"><div><h2>恢复评分</h2><p>恢复评分会同步统一 API，离线时保留本地缓存。</p></div></div>
              <form class="fit-form" @submit.prevent="saveRecovery">
                <div class="form-grid">
                  <label class="field">日期<el-date-picker v-model="recoveryForm.date" type="date" value-format="YYYY-MM-DD" /></label>
                  <label class="field">睡眠小时<el-input-number v-model="recoveryForm.sleepHours" :min="0" :max="14" :step="0.5" :precision="1" controls-position="right" /></label>
                  <label v-for="f in recoveryScoreFields" :key="f.key" class="field">{{ f.label }}<el-slider v-model="recoveryForm[f.key]" :min="0" :max="f.max" show-stops /></label>
                </div>
                <div class="recognition-state" data-state="success">{{ computedRecovery.statusAdvice }}</div>
                <div class="actions"><el-button type="primary" :loading="saving === 'recovery'" @click="saveRecovery">保存恢复状态</el-button></div>
              </form>
            </div>
          </article>
          <aside class="stack">
            <article class="glass-card result-panel status-card">
              <div class="glass-card-inner">
                <div class="card-head"><div><h3>恢复预览</h3><p>实时计算今日恢复分。</p></div></div>
                <div class="deficit-number" :class="{ 'over-limit': computedRecovery.score < 55 }">{{ computedRecovery.score }}</div>
                <div class="deficit-subtitle">{{ computedRecovery.statusLabel }} · {{ latestRecoveryText }}</div>
              </div>
            </article>
            <article class="glass-card">
              <div class="glass-card-inner">
                <div class="card-head"><div><h3>恢复趋势</h3><p>最近记录的恢复评分变化。</p></div></div>
                <div class="chart-wrap" aria-label="恢复趋势图">
                  <div ref="recoveryChartEl" class="fitness-chart-inner"></div>
                  <span v-if="!hasRecoveryTrend" class="chart-empty">保存恢复状态后生成趋势图</span>
                </div>
              </div>
            </article>
          </aside>
          <article class="glass-card full-row history-card">
            <div class="glass-card-inner">
              <div class="card-head"><div><h3>恢复历史</h3><p>在线读取统一 API；接口不可用时使用浏览器离线缓存。</p></div></div>
              <div class="log-list">
                <div v-for="row in recoveryLogs" :key="row.id" class="log-item">
                  <div class="log-item-main"><strong>{{ row.score }} 分 · {{ row.statusLabel }}</strong><small>{{ row.date }}</small></div>
                  <span class="log-item-detail">睡眠 {{ row.sleepHours }}h / 压力 {{ row.stress }}</span>
                </div>
                <p v-if="!recoveryLogs.length" class="empty">暂无恢复记录。</p>
              </div>
            </div>
          </article>
        </section>

        <section v-show="activeSection === 'consult'" class="module-grid workbench-section">
          <article class="glass-card priority-card clinical-card">
            <div class="glass-card-inner">
              <div class="card-head"><div><h2>身体问题咨询</h2><p>只做健身范围内建议；胸闷、晕厥、急性剧痛等红线直接提示就医。</p></div></div>
              <form class="fit-form" @submit.prevent="saveConsult">
                <div class="form-grid">
                  <label class="field">日期<el-date-picker v-model="consultForm.date" type="date" value-format="YYYY-MM-DD" /></label>
                  <label class="field">部位<el-input v-model="consultForm.area" placeholder="膝 / 腰 / 肩 / 体态" /></label>
                  <label class="field">风险级别<el-select v-model="consultForm.level"><el-option label="可训练调整" value="green" /><el-option label="谨慎观察" value="yellow" /><el-option label="停止训练并就医" value="red" /></el-select></label>
                  <label class="field field-wide">描述<el-input v-model="consultForm.text" type="textarea" :rows="4" placeholder="例如：深蹲时膝盖前侧疼，未肿胀" /></label>
                </div>
                <div class="actions"><el-button type="primary" :loading="saving === 'consult'" @click="saveConsult">保存咨询</el-button></div>
              </form>
            </div>
          </article>
          <aside class="stack">
            <article class="glass-card result-panel clinical-card">
              <div class="glass-card-inner">
                <div class="card-head"><div><h3>风险提示</h3><p>根据选择的风险级别给出建议。</p></div></div>
                <div class="advice-box" :class="{ 'clinical-advice': consultForm.level === 'red' }">{{ consultLevelTitle(consultForm.level) }}</div>
              </div>
            </article>
          </aside>
          <article class="glass-card full-row history-card">
            <div class="glass-card-inner">
              <div class="card-head"><div><h3>咨询历史</h3><p>在线读取统一 API；IndexedDB 只补充离线待同步记录。</p></div></div>
              <div class="log-list">
                <div v-for="row in consultLogs" :key="row.id" class="log-item">
                  <div class="log-item-main"><strong>{{ row.area || row.title || '身体咨询' }}</strong><small>{{ row.date }}</small></div>
                  <span class="log-item-detail">{{ row.text }}</span>
                </div>
                <p v-if="!consultLogs.length" class="empty">暂无咨询记录。</p>
              </div>
            </div>
          </article>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { useStorage } from '@vueuse/core'
import dayjs from 'dayjs'
import type { ECharts } from 'echarts/core'
import {
  createAssessmentLog,
  createBodyMetric,
  createConsultLog,
  createNutritionLog,
  createRecoveryLog,
  createWorkoutLog,
  fetchFitnessSnapshot,
  type FitnessAssessmentLog,
  type FitnessBodyMetric,
  type FitnessConsultLog,
  type FitnessNutritionLog,
  type FitnessRecoveryLog,
  type FitnessSnapshot,
  type FitnessWorkoutLog,
  type NutritionSummary
} from './api'

type SavingKey = '' | 'nutrition' | 'workout' | 'metric' | 'recovery' | 'assessment' | 'consult'
type RecognitionState = { type: 'success' | 'warning' | 'error' | 'info', message: string }
type AssessmentSectionKey = 'baseline' | 'girths' | 'fms' | 'posture'
type OperationFeedback = { type: 'loading' | 'success' | 'error', title: string, detail: string }
type AssessmentForm = {
  date: string
  goal: string
  heightCm: number
  weightKg?: number
  age: number
  sex: 'male' | 'female'
  activity: number
  waistCm?: number
  bodyFatPct?: number
  hipCm?: number
  chestCm?: number
  armCm?: number
  thighCm?: number
  [key: string]: string | number | undefined
}
type FmsScoreKey = 'deepSquat' | 'hurdleStep' | 'inlineLunge' | 'shoulderMobility' | 'activeSlr' | 'trunkStability' | 'rotaryStability'
type RecognizedMeal = {
  food: string
  items: Record<string, unknown>[]
  calories: number
  proteinG: number
  carbsG: number
  fatG: number
  confidence: number
  warnings: string[]
  source: string
}

const selectedDate = ref(dayjs().format('YYYY-MM-DD'))
const activeSection = useStorage('niu-vue-fitness-section', 'dashboard')
const loading = ref(false)
const saving = ref<SavingKey>('')
const loadError = ref('')
const recognizing = ref(false)
const activeAssessmentSection = ref<AssessmentSectionKey>('baseline')
const postureFlags = ref<string[]>([])
const selectedPhoto = ref<File | null>(null)
const recognizedMeal = ref<RecognizedMeal | null>(null)
const recognitionState = ref<RecognitionState | null>(null)
const operationFeedback = ref<OperationFeedback | null>(null)
const weightChartEl = ref<HTMLDivElement | null>(null)
const recoveryChartEl = ref<HTMLDivElement | null>(null)
let weightChart: ECharts | null = null
let recoveryChart: ECharts | null = null
let chartRuntimePromise: Promise<typeof import('./chartRuntime')> | null = null

const todaySummary = ref<NutritionSummary>({ date: selectedDate.value, count: 0, calories: 0, proteinG: 0, carbsG: 0, fatG: 0 })
const weeklySummary = ref<FitnessSnapshot['weekly']>({
  from: selectedDate.value,
  to: selectedDate.value,
  nutritionCount: 0,
  calories: 0,
  proteinG: 0,
  workoutCount: 0,
  workoutMinutes: 0,
  workoutCalories: 0,
  latestMetric: null,
  metricsCount: 0
})
const profile = ref<Record<string, unknown>>({})
const nutritionLogs = ref<FitnessNutritionLog[]>([])
const workoutLogs = ref<FitnessWorkoutLog[]>([])
const bodyMetrics = ref<FitnessBodyMetric[]>([])
const recoveryLogs = ref<FitnessRecoveryLog[]>([])
const assessmentLogs = ref<FitnessAssessmentLog[]>([])
const consultLogs = ref<FitnessConsultLog[]>([])
const workoutRecommendation = ref<string[]>([])

const nutritionForm = reactive({ date: selectedDate.value, food: '', calories: 0, proteinG: 0, carbsG: 0, fatG: 0 })
const photoForm = reactive({ description: '' })
const workoutForm = reactive({ date: selectedDate.value, name: '', durationMin: 45, intensity: 'medium', calories: 0, note: '' })
const metricForm = reactive({ date: selectedDate.value, weightKg: undefined as number | undefined, bodyFatPct: undefined as number | undefined, waistCm: undefined as number | undefined, note: '' })
const recoveryForm = reactive({ date: selectedDate.value, sleepHours: 7, sleepQuality: 3, stress: 2, soreness: 2, lastRpe: 7 })
const assessmentForm = reactive<AssessmentForm>({
  date: selectedDate.value,
  goal: 'recomp',
  heightCm: 175,
  weightKg: undefined,
  age: 32,
  sex: 'male',
  activity: 1.45,
  waistCm: undefined,
  bodyFatPct: undefined,
  hipCm: undefined,
  chestCm: undefined,
  armCm: undefined,
  thighCm: undefined
})
const consultForm = reactive({ date: selectedDate.value, area: '', text: '', level: 'green' })
const fmsScores = reactive<Record<FmsScoreKey, number>>({
  deepSquat: 2,
  hurdleStep: 2,
  inlineLunge: 2,
  shoulderMobility: 2,
  activeSlr: 2,
  trunkStability: 2,
  rotaryStability: 2
})

const nutritionNumberFields = [
  { key: 'calories' as const, label: '热量 kcal' },
  { key: 'proteinG' as const, label: '蛋白 g' },
  { key: 'carbsG' as const, label: '碳水 g' },
  { key: 'fatG' as const, label: '脂肪 g' }
]
const recoveryScoreFields = [
  { key: 'sleepQuality' as const, label: '睡眠质量', max: 5 },
  { key: 'stress' as const, label: '压力', max: 5 },
  { key: 'soreness' as const, label: '酸痛', max: 5 },
  { key: 'lastRpe' as const, label: '最近 RPE', max: 10 }
]
const assessmentSections: Array<{ key: AssessmentSectionKey, index: string, label: string, hint: string }> = [
  { key: 'baseline', index: '01', label: '基础信息', hint: 'BMI / TDEE' },
  { key: 'girths', index: '02', label: '围度数据', hint: '可选体围' },
  { key: 'fms', index: '03', label: 'FMS 动作', hint: '低分风险' },
  { key: 'posture', index: '04', label: '体态观察', hint: '训练限制' }
]
const assessmentGirthFields = [
  { key: 'hipCm' as const, label: '臀围 cm' },
  { key: 'chestCm' as const, label: '胸围 cm' },
  { key: 'armCm' as const, label: '上臂 cm' },
  { key: 'thighCm' as const, label: '大腿 cm' }
]
const fmsFields: Array<{ key: FmsScoreKey, label: string }> = [
  { key: 'deepSquat', label: '深蹲' },
  { key: 'hurdleStep', label: '跨栏步' },
  { key: 'inlineLunge', label: '弓步' },
  { key: 'shoulderMobility', label: '肩灵活' },
  { key: 'activeSlr', label: '直腿抬高' },
  { key: 'trunkStability', label: '躯干稳定' },
  { key: 'rotaryStability', label: '旋转稳定' }
]
const postureOptions = ['圆肩', '骨盆前倾', '膝内扣', '久坐髋紧', '头前伸', '足弓塌陷']

const latestMetric = computed(() => bodyMetrics.value[0])
const latestRecovery = computed(() => recoveryLogs.value[0])
const hasWeightTrend = computed(() => bodyMetrics.value.some((item) => item.weightKg))
const hasRecoveryTrend = computed(() => recoveryLogs.value.some((item) => item.score))
const targets = computed(() => ({
  calories: Number(profile.value.targetCalories || profile.value.calorieTarget || 2100),
  proteinG: Number(profile.value.proteinTarget || 150),
  carbsG: Number(profile.value.carbsTarget || 240),
  fatG: Number(profile.value.fatTarget || 70)
}))
const kpiCards = computed(() => [
  { label: '今日摄入', value: `${todaySummary.value.calories || 0}`, detail: 'kcal' },
  { label: '本周训练', value: `${weeklySummary.value.workoutMinutes || 0}`, detail: '分钟' },
  { label: '最新体重', value: latestMetric.value?.weightKg ? latestMetric.value.weightKg.toFixed(1) : '--', detail: 'kg' },
  { label: '恢复状态', value: latestRecovery.value?.score ? `${latestRecovery.value.score}` : '--', detail: latestRecovery.value?.statusLabel || '等待打卡' }
])
const macroRows = computed(() => [
  macroRow('热量', todaySummary.value.calories, targets.value.calories, 'kcal'),
  macroRow('蛋白', todaySummary.value.proteinG, targets.value.proteinG, 'g'),
  macroRow('碳水', todaySummary.value.carbsG, targets.value.carbsG, 'g'),
  macroRow('脂肪', todaySummary.value.fatG, targets.value.fatG, 'g')
])
const latestMetricText = computed(() => {
  const metric = latestMetric.value
  if (!metric) return '暂无记录'
  return [metric.weightKg ? `${metric.weightKg}kg` : '', metric.bodyFatPct ? `${metric.bodyFatPct}%` : '', metric.waistCm ? `${metric.waistCm}cm` : ''].filter(Boolean).join(' / ')
})
const latestRecoveryText = computed(() => {
  const recovery = latestRecovery.value
  if (!recovery) return '暂无记录'
  return `${recovery.score} 分 · ${recovery.statusLabel || '未标注'}`
})
const computedRecovery = computed(() => {
  const sleepScore = Math.min(40, recoveryForm.sleepHours * 5)
  const qualityScore = recoveryForm.sleepQuality * 8
  const stressPenalty = recoveryForm.stress * 6
  const sorenessPenalty = recoveryForm.soreness * 5
  const rpePenalty = Math.max(0, recoveryForm.lastRpe - 7) * 6
  const score = Math.max(0, Math.min(100, Math.round(sleepScore + qualityScore + 35 - stressPenalty - sorenessPenalty - rpePenalty)))
  if (score >= 75) return { score, statusLabel: '绿色', statusAdvice: '恢复良好，可以按计划训练。' }
  if (score >= 55) return { score, statusLabel: '黄色', statusAdvice: '恢复一般，建议降低 10-30% 训练量。' }
  return { score, statusLabel: '红色', statusAdvice: '恢复不足，优先主动恢复或休息。' }
})
const fmsTotal = computed(() => Object.values(fmsScores).reduce((sum, value) => sum + Number(value || 0), 0))
const fmsRiskLabel = computed(() => {
  if (fmsTotal.value >= 17) return '低'
  if (fmsTotal.value >= 14) return '中'
  return '高'
})
const assessmentPreview = computed(() => {
  const weight = Number(assessmentForm.weightKg || latestMetric.value?.weightKg || 0)
  const height = Number(assessmentForm.heightCm || profile.value.heightCm || 175)
  const age = Number(assessmentForm.age || 32)
  const activity = Number(assessmentForm.activity || 1.45)
  const bmi = weight && height ? Number((weight / ((height / 100) ** 2)).toFixed(1)) : 0
  const bmrBase = assessmentForm.sex === 'female'
    ? 10 * weight + 6.25 * height - 5 * age - 161
    : 10 * weight + 6.25 * height - 5 * age + 5
  const bmr = weight ? Math.round(bmrBase) : 0
  return {
    bmi: bmi ? String(bmi) : '--',
    bmr: bmr ? String(bmr) : '--',
    tdee: bmr ? String(Math.round(bmr * activity)) : '--'
  }
})
const activeAssessmentLabel = computed(() => assessmentSections.find((section) => section.key === activeAssessmentSection.value)?.label || '基础信息')
const activeAssessmentIndex = computed(() => Math.max(0, assessmentSections.findIndex((section) => section.key === activeAssessmentSection.value)))
const assessmentProgress = computed(() => ((activeAssessmentIndex.value + 1) / assessmentSections.length) * 100)
const nextAssessmentSection = computed<AssessmentSectionKey>(() => {
  return assessmentSections[(activeAssessmentIndex.value + 1) % assessmentSections.length].key
})
const recentRecords = computed(() => [
  ...nutritionLogs.value.slice(0, 4).map((item) => ({ id: `n-${item.id}`, date: item.date, type: '饮食', title: item.food, detail: `${item.calories} kcal / 蛋白 ${item.proteinG}g` })),
  ...workoutLogs.value.slice(0, 4).map((item) => ({ id: `w-${item.id}`, date: item.date, type: '训练', title: item.name, detail: `${item.durationMin} 分钟 / ${intensityLabel(item.intensity)}` })),
  ...bodyMetrics.value.slice(0, 4).map((item) => ({ id: `m-${item.id}`, date: item.date, type: '体征', title: item.weightKg ? `${item.weightKg}kg` : '身体指标', detail: item.note || `${item.bodyFatPct || '--'}% / ${item.waistCm || '--'}cm` }))
].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10))
const assessmentAndConsultRows = computed(() => [
  ...assessmentLogs.value.map((item) => ({ id: `a-${item.id}`, date: item.date, type: '评估', title: goalLabel(item.goal), detail: `FMS ${item.fmsTotal || 0} / BMI ${item.bmi || '--'}` })),
  ...consultLogs.value.map((item) => ({ id: `c-${item.id}`, date: item.date, type: '咨询', title: item.area || item.title || '身体咨询', detail: item.text }))
].sort((a, b) => b.date.localeCompare(a.date)))

const navSections = [
  { key: 'dashboard', label: '总览' },
  { key: 'assessment', label: '评估' },
  { key: 'training', label: '训练' },
  { key: 'nutrition', label: '营养' },
  { key: 'recovery', label: '恢复' },
  { key: 'consult', label: '咨询' }
]
const heroMetrics = computed(() => [
  { value: latestMetric.value?.weightKg ? latestMetric.value.weightKg.toFixed(1) : '--', label: '体重趋势 kg' },
  { value: `${todaySummary.value.calories || 0}`, label: '今日摄入 kcal' },
  { value: latestRecovery.value?.score ? `${latestRecovery.value.score}` : '--', label: '恢复信号' },
  { value: `${weeklySummary.value.workoutCount || 0}`, label: '本周训练' }
])
const profileRows = computed(() => {
  const p = profile.value
  const val = (v: unknown, suffix = '') => {
    const s = v === undefined || v === null || v === '' ? '' : String(v)
    return s ? (suffix ? `${s} ${suffix}` : s) : '--'
  }
  return [
    { label: '身高', value: val(p.heightCm, 'cm') },
    { label: '体重', value: latestMetric.value?.weightKg ? `${latestMetric.value.weightKg} kg` : '--' },
    { label: '年龄', value: val(p.age) },
    { label: '目标', value: goalLabel(String(p.goal || 'recomp')) },
    { label: '活动系数', value: val(p.activity) },
    { label: '目标热量', value: targets.value.calories ? `${targets.value.calories} kcal` : '--' }
  ]
})
const caloriePercent = computed(() => targets.value.calories ? Math.min(100, Math.round((Number(todaySummary.value.calories) || 0) / targets.value.calories * 100)) : 0)
const calorieDeg = computed(() => Math.round(caloriePercent.value / 100 * 360))
const ringStyle = computed(() => ({ background: `conic-gradient(var(--fitness-good) ${calorieDeg.value}deg, rgba(245,248,244,0.08) 0)` }))
const deficitValue = computed(() => {
  const tdee = Number(assessmentPreview.value.tdee !== '--' ? assessmentPreview.value.tdee : targets.value.calories) || 0
  return Math.round(tdee - (Number(todaySummary.value.calories) || 0))
})
const weightDelta = computed(() => {
  const rows = bodyMetrics.value.filter((item) => item.weightKg)
  if (rows.length < 2) return '--'
  const latest = Number(rows[0].weightKg || 0)
  const oldest = Number(rows[Math.min(6, rows.length - 1)].weightKg || 0)
  const delta = latest - oldest
  return delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)
})
const bmiText = computed(() => {
  const weight = latestMetric.value?.weightKg
  const height = Number(profile.value.heightCm || 0)
  if (!weight || !height) return '--'
  return (weight / ((height / 100) ** 2)).toFixed(1)
})
const assessmentHistory = computed(() => assessmentAndConsultRows.value.filter((row) => row.type === '评估'))
watch(activeSection, (value) => {
  syncSectionToUrl(value)
  if (value === 'dashboard' || value === 'recovery') nextTick(() => scheduleChartRender())
})

onMounted(() => {
  window.addEventListener('resize', resizeCharts)
  const sectionFromUrl = readSectionFromUrl()
  if (sectionFromUrl) activeSection.value = sectionFromUrl
  load()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  weightChart?.dispose()
  recoveryChart?.dispose()
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const snapshot = await fetchFitnessSnapshot(selectedDate.value)
    todaySummary.value = snapshot.today
    weeklySummary.value = snapshot.weekly
    profile.value = snapshot.profile
    nutritionLogs.value = snapshot.nutrition
    workoutLogs.value = snapshot.workouts
    bodyMetrics.value = snapshot.metrics
    recoveryLogs.value = snapshot.recovery
    assessmentLogs.value = snapshot.assessments
    consultLogs.value = snapshot.consults
    workoutRecommendation.value = snapshot.workoutRecommendation?.recommendations || []
    await nextTick()
    scheduleChartRender()
  } catch (error: any) {
    loadError.value = error.message || '塑形馆数据读取失败'
  } finally {
    loading.value = false
  }
}

function handlePhotoChange(uploadFile: any) {
  selectedPhoto.value = uploadFile.raw || null
  recognizedMeal.value = null
  recognitionState.value = selectedPhoto.value ? { type: 'info', message: `已选择 ${selectedPhoto.value.name}` } : null
}

function clearPhoto() {
  selectedPhoto.value = null
  recognizedMeal.value = null
  recognitionState.value = null
}

async function recognizePhoto() {
  if (!selectedPhoto.value) {
    recognitionState.value = { type: 'error', message: '请先选择餐食图片。' }
    return
  }
  recognizing.value = true
  try {
    const body = new FormData()
    body.append('photo', selectedPhoto.value)
    body.append('description', photoForm.description || '')
    const response = await fetch('/niu-secretary/fitness/api/agent/nutrition-recognize', { method: 'POST', body })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.message || `图片识别失败：${response.status}`)
    recognizedMeal.value = normalizeRecognizedMeal(payload, payload.source || 'agent')
    recognitionState.value = { type: 'success', message: '识别完成，请确认后写入营养日志。' }
  } catch (error: any) {
    recognitionState.value = { type: 'error', message: error.message || '图片识别服务暂不可用。' }
  } finally {
    recognizing.value = false
  }
}

function estimatePhoto() {
  if (!selectedPhoto.value && !photoForm.description.trim()) {
    recognitionState.value = { type: 'error', message: '需要图片或描述才能估算。' }
    return
  }
  recognizedMeal.value = estimateMealLocally(selectedPhoto.value, photoForm.description)
  recognitionState.value = { type: 'warning', message: '已生成本地估算，未经过视觉模型，请确认后写入。' }
}

function applyRecognizedToForm() {
  if (!recognizedMeal.value) return
  nutritionForm.food = recognizedMeal.value.food
  nutritionForm.calories = recognizedMeal.value.calories
  nutritionForm.proteinG = recognizedMeal.value.proteinG
  nutritionForm.carbsG = recognizedMeal.value.carbsG
  nutritionForm.fatG = recognizedMeal.value.fatG
  activeSection.value = 'nutrition'
}

async function saveRecognizedNutrition() {
  if (!recognizedMeal.value) return
  const saved = await saveWithReload('nutrition', () => createNutritionLog({
    date: selectedDate.value,
    food: recognizedMeal.value?.food || '',
    calories: recognizedMeal.value?.calories || 0,
    proteinG: recognizedMeal.value?.proteinG || 0,
    carbsG: recognizedMeal.value?.carbsG || 0,
    fatG: recognizedMeal.value?.fatG || 0,
    items: recognizedMeal.value?.items || [],
    confidence: recognizedMeal.value?.confidence || 0,
    warnings: recognizedMeal.value?.warnings || [],
    imageName: selectedPhoto.value?.name || '',
    source: recognizedMeal.value?.source || 'vue-photo'
  }))
  if (saved) recognizedMeal.value = null
}

async function saveNutrition() {
  if (!nutritionForm.food.trim()) return ElMessage.warning('请填写食物')
  const saved = await saveWithReload('nutrition', () => createNutritionLog({ ...nutritionForm }))
  if (!saved) return
  nutritionForm.food = ''
  nutritionForm.calories = 0
  nutritionForm.proteinG = 0
  nutritionForm.carbsG = 0
  nutritionForm.fatG = 0
}

async function saveWorkout() {
  if (!workoutForm.name.trim()) return ElMessage.warning('请填写训练名称')
  const saved = await saveWithReload('workout', () => createWorkoutLog({ ...workoutForm }))
  if (!saved) return
  workoutForm.name = ''
  workoutForm.note = ''
}

async function saveMetric() {
  if (!metricForm.weightKg && !metricForm.bodyFatPct && !metricForm.waistCm) return ElMessage.warning('至少填写一个身体指标')
  const saved = await saveWithReload('metric', () => createBodyMetric({ ...metricForm }))
  if (!saved) return
  metricForm.note = ''
}

async function saveRecovery() {
  await saveWithReload('recovery', () => createRecoveryLog({ ...recoveryForm, ...computedRecovery.value }))
}

async function saveAssessment() {
  const weight = assessmentForm.weightKg || latestMetric.value?.weightKg || 0
  const heightCm = Number(assessmentForm.heightCm || profile.value.heightCm || 175)
  const bmi = weight && heightCm ? Number((weight / ((heightCm / 100) ** 2)).toFixed(1)) : undefined
  const payload = {
    ...assessmentForm,
    bmi,
    bmr: assessmentPreview.value.bmr,
    tdee: assessmentPreview.value.tdee,
    fmsTotal: fmsTotal.value,
    fmsScores: { ...fmsScores },
    fmsRisk: fmsRiskLabel.value,
    postureFlags: [...postureFlags.value]
  }
  await saveWithReload('assessment', () => createAssessmentLog({
    ...assessmentForm,
    bmi,
    fmsTotal: fmsTotal.value,
    payload
  }))
}

async function saveConsult() {
  if (!consultForm.text.trim()) return ElMessage.warning('请填写咨询描述')
  const saved = await saveWithReload('consult', () => createConsultLog({ ...consultForm, title: consultLevelTitle(consultForm.level), payload: { ...consultForm } }))
  if (!saved) return
  consultForm.area = ''
  consultForm.text = ''
}

async function saveWithReload(key: SavingKey, fn: () => Promise<unknown>): Promise<boolean> {
  if (saving.value) return false
  saving.value = key
  operationFeedback.value = { type: 'loading', title: '正在保存', detail: '数据将写入统一 Action 接口，完成后刷新当前视图。' }
  try {
    await fn()
    operationFeedback.value = { type: 'success', title: '保存成功', detail: '后端已确认写入，已请求刷新当前数据。' }
    ElMessage.success('已保存')
    await load()
    return true
  } catch (error: any) {
    const detail = error.message || '保存失败'
    operationFeedback.value = { type: 'error', title: '保存失败', detail }
    ElMessage.error(detail)
    return false
  } finally {
    saving.value = ''
  }
}

function macroRow(label: string, value: number, target: number, unit: string) {
  const percent = target ? Math.min(100, Math.round((Number(value || 0) / target) * 100)) : 0
  return { label, value: Number(value || 0), target, unit, percent, status: percent >= 100 ? 'success' : undefined }
}

async function loadChartRuntime() {
  if (!chartRuntimePromise) {
    chartRuntimePromise = import('./chartRuntime').catch((error) => {
      chartRuntimePromise = null
      throw error
    })
  }
  return chartRuntimePromise
}

async function renderCharts() {
  const { init } = await loadChartRuntime()
  renderWeightChart(init)
  renderRecoveryChart(init)
}

function scheduleChartRender() {
  window.requestAnimationFrame(async () => {
    try {
      await renderCharts()
    } catch (error) {
      console.warn('fitness chart render skipped', error)
    }
  })
}

function renderWeightChart(initChart: typeof import('echarts/core')['init']) {
  if (!weightChartEl.value || !weightChartEl.value.offsetWidth) return
  weightChart ||= initChart(weightChartEl.value)
  const rows = [...bodyMetrics.value].reverse().filter((item) => item.weightKg)
  weightChart.setOption({
    grid: { left: 42, right: 16, top: 24, bottom: 34 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: rows.map((item) => item.date) },
    yAxis: { type: 'value', scale: true },
    series: [{ name: '体重 kg', type: 'line', smooth: true, data: rows.map((item) => item.weightKg), areaStyle: {} }]
  })
}

function renderRecoveryChart(initChart: typeof import('echarts/core')['init']) {
  if (!recoveryChartEl.value || !recoveryChartEl.value.offsetWidth) return
  recoveryChart ||= initChart(recoveryChartEl.value)
  const rows = [...recoveryLogs.value].reverse().filter((item) => item.score)
  recoveryChart.setOption({
    grid: { left: 42, right: 16, top: 24, bottom: 34 },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: rows.map((item) => item.date) },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{ name: '恢复分', type: 'bar', data: rows.map((item) => item.score), itemStyle: { borderRadius: 4 } }]
  })
}

function resizeCharts() {
  weightChart?.resize()
  recoveryChart?.resize()
}

function goNextAssessmentSection() {
  activeAssessmentSection.value = nextAssessmentSection.value
}

function readSectionFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const section = params.get('section') || window.location.hash.replace(/^#/, '')
  return navSections.some((item) => item.key === section) ? section : ''
}

function syncSectionToUrl(section: string) {
  if (!navSections.some((item) => item.key === section)) return
  const url = new URL(window.location.href)
  if (section === 'dashboard') {
    url.searchParams.delete('section')
  } else {
    url.searchParams.set('section', section)
  }
  window.history.replaceState(null, '', `${url.pathname}${url.search}${url.hash}`)
}

function normalizeRecognizedMeal(data: any, source: string): RecognizedMeal {
  return {
    food: data.food || data.name || photoForm.description || selectedPhoto.value?.name || '图片餐食',
    items: Array.isArray(data.items) ? data.items : [],
    calories: clampNumber(data.calories, 0, 5000),
    proteinG: clampNumber(data.proteinG ?? data.protein, 0, 300),
    carbsG: clampNumber(data.carbsG ?? data.carbs, 0, 600),
    fatG: clampNumber(data.fatG ?? data.fat, 0, 300),
    confidence: Math.max(0, Math.min(1, Number(data.confidence || 0))),
    warnings: Array.isArray(data.warnings) ? data.warnings.map(String) : [],
    source
  }
}

function estimateMealLocally(file: File | null, description: string): RecognizedMeal {
  const text = String(description || '').toLowerCase()
  let calories = 520
  let proteinG = 28
  let carbsG = 62
  let fatG = 18
  const items: Record<string, unknown>[] = []
  if (/奶茶|甜品|炸|薯|burger|pizza/.test(text)) {
    calories += 260
    carbsG += 34
    fatG += 12
    items.push({ name: '高热量配餐线索', calories: 260, carbsG: 34, fatG: 12 })
  }
  if (/鸡|牛|鱼|蛋|protein|肉/.test(text)) {
    calories += 120
    proteinG += 22
    fatG += 4
    items.push({ name: '蛋白质食物线索', calories: 120, proteinG: 22, fatG: 4 })
  }
  if (/米饭|面|粉|粥|bread|rice/.test(text)) {
    calories += 170
    carbsG += 42
    items.push({ name: '主食线索', calories: 170, carbsG: 42 })
  }
  if (/沙拉|蔬菜|青菜/.test(text)) {
    calories -= 90
    carbsG -= 18
    fatG -= 3
    items.push({ name: '蔬菜线索', calories: 60, proteinG: 2, carbsG: 8, fatG: 1 })
  }
  if (file && file.size > 2_000_000) calories += 80
  return {
    food: description || file?.name || '图片餐食',
    items,
    calories: clampNumber(calories, 0, 5000),
    proteinG: clampNumber(proteinG, 0, 300),
    carbsG: clampNumber(carbsG, 0, 600),
    fatG: clampNumber(fatG, 0, 300),
    confidence: 0.42,
    warnings: ['本地估算未调用视觉模型。'],
    source: 'local-estimate'
  }
}

function clampNumber(value: unknown, min: number, max: number) {
  const n = Number(value || 0)
  return Math.max(min, Math.min(max, Math.round(n)))
}

function intensityLabel(intensity: string) {
  if (intensity === 'high') return '高'
  if (intensity === 'low') return '低'
  return '中'
}

function intensityTag(intensity: string) {
  if (intensity === 'high') return 'danger'
  if (intensity === 'low') return 'info'
  return 'warning'
}

function goalLabel(goal = '') {
  return ({ fat_loss: '减脂', muscle_gain: '增肌', recomp: '身体重组', maintain: '维持' } as Record<string, string>)[goal] || goal || '未设置'
}

function consultLevelTitle(level: string) {
  return ({ green: '可在健身范围内调整', yellow: '谨慎观察', red: '停止训练并就医' } as Record<string, string>)[level] || '身体咨询'
}
</script>
