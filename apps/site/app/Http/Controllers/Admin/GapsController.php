<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Http\Requests\Admin\PeriodRequest;
use App\Models\GapTask;
use App\Services\Analytics\QuestionInsights;
use Carbon\CarbonImmutable;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

/**
 * Knowledge gaps: what visitors asked that the index could not answer,
 * grouped from the real question log, with the team's follow-up tasks.
 */
class GapsController extends Controller
{
    public function index(PeriodRequest $request, QuestionInsights $insights): Response
    {
        $start = $request->windowStart();
        $today = CarbonImmutable::today();
        $gaps = $insights->gaps($start, $today, $start->subDays($request->period()));

        $keys = array_column([...$gaps['insufficient'], ...$gaps['outOfScope']], 'key');
        $tasks = GapTask::whereIn('group_key', $keys)->get()->keyBy('group_key');
        $withTask = fn (array $group) => [...$group, 'task' => isset($tasks[$group['key']]) ? [
            'id' => $tasks[$group['key']]->id,
            'status' => $tasks[$group['key']]->status,
        ] : null];

        return Inertia::render('admin/Gaps', [
            'period' => $request->period(),
            'insufficient' => array_map($withTask, $gaps['insufficient']),
            'outOfScope' => array_map($withTask, $gaps['outOfScope']),
            'sections' => array_slice($insights->sections($start, $today), 0, 10),
            'openTasks' => GapTask::where('status', 'open')->count(),
        ]);
    }

    public function storeTask(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'group_key' => ['required', 'string', 'size:40'],
            'kind' => ['required', Rule::in(['insufficient', 'out_of_scope'])],
            'title' => ['required', 'string', 'max:300'],
        ]);

        $task = GapTask::firstOrNew(['group_key' => $data['group_key']]);
        $task->fill($data);
        $task->status = 'open';
        $task->completed_at = null;
        $task->created_by ??= $request->user()->id;
        $task->save();

        return back()->with('toast', 'أُنشئت مهمة لفريق المحتوى.');
    }

    public function updateTask(Request $request, GapTask $task): RedirectResponse
    {
        $data = $request->validate(['status' => ['required', Rule::in(['open', 'done'])]]);

        $task->status = $data['status'];
        $task->completed_at = $data['status'] === 'done' ? now() : null;
        $task->save();

        return back()->with('toast', $data['status'] === 'done' ? 'أُغلقت المهمة.' : 'أُعيد فتح المهمة.');
    }
}
